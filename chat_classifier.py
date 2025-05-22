
import os
import json
import asyncio
import itertools
import logging
import ssl
import httpx

try:
    import certifi
    _CA_BUNDLE = certifi.where()
except Exception:  # pragma: no cover - optional dependency
    certifi = None
    _CA_BUNDLE = None

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

# Remove proxy env vars to avoid TLS interception
for _proxy_var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
    if os.environ.pop(_proxy_var, None):
        logger.warning("Removed %s environment variable", _proxy_var)

if _CA_BUNDLE:
    logger.info("Using CA bundle at %s", _CA_BUNDLE)
    _SSL_CONTEXT = ssl.create_default_context(cafile=_CA_BUNDLE)
else:  # pragma: no cover - fallback when certifi missing
    _SSL_CONTEXT = ssl.create_default_context()

API_URL = "https://api.openai.com/v1/chat/completions"

# Support optional key rotation when OPENAI_API_KEYS is set to a comma-separated
# list of keys. Falls back to the single OPENAI_API_KEY environment variable.
_API_KEYS = [
    k.strip()
    for k in os.getenv("OPENAI_API_KEYS", os.getenv("OPENAI_API_KEY", "")).split(",")
    if k.strip()
]
_KEYS_CYCLE = itertools.cycle(_API_KEYS) if _API_KEYS else itertools.cycle([""])


def _next_api_key() -> str:
    """Return the next API key in round-robin order."""
    if not _API_KEYS:
        raise RuntimeError(
            "No OpenAI API key provided. Set OPENAI_API_KEY or OPENAI_API_KEYS"
        )
    return next(_KEYS_CYCLE)


def _post(url: str, *, headers: dict, json_payload: dict) -> httpx.Response:
    """Internal helper to POST with certificate validation fallback."""
    try:
        return httpx.post(
            url, headers=headers, json=json_payload, timeout=30, verify=_SSL_CONTEXT
        )
    except httpx.HTTPError as e:  # pragma: no cover - network edge case
        logger.warning("SSL request error: %s; retrying without verification", e)
        return httpx.post(url, headers=headers, json=json_payload, timeout=30, verify=False)


async def _post_async(
    client: httpx.AsyncClient, url: str, *, headers: dict, json_payload: dict
) -> httpx.Response:
    try:
        return await client.post(
            url, headers=headers, json=json_payload, timeout=30, verify=_SSL_CONTEXT
        )
    except httpx.HTTPError as e:  # pragma: no cover - network edge case
        logger.warning(
            "SSL request error: %s; retrying without verification", e
        )
        return await client.post(
            url, headers=headers, json=json_payload, timeout=30, verify=False
        )

def chat_classify(
    labels: list[str],
    web_labels: list[str],
    expected_content=None,
) -> dict:
    """Classify image tags using ChatGPT.

    Parameters
    ----------
    labels : list[str]
        Generic labels returned from Vision API.
    web_labels : list[str]
        Web entity labels returned from Vision API.
    expected_content : list[str] | None, optional
        Additional content tags to consider for matching. Defaults to ``[]``.
    """

    expected_content = expected_content or []
    prompt = f"""
You are an ad tagging assistant. Based on the following image data:

Generic Labels:
{', '.join(labels)}

Web Entities:
{', '.join(web_labels)}

Return a JSON object with:
- "audience": describe the most likely audience (e.g., mom, teen, athlete, grandma)
- "product": name the product shown, and keep it specific if a brand is mentioned
- "angle": the emotional or marketing angle (e.g., natural beauty, wellness, performance)
- "descriptors": a short list of helpful visual or thematic descriptors (e.g., outdoors, close-up, vibrant colors)

Use the following expected content tags to set ``match_content`` to the closest tag or ``unknown`` if nothing is relevant:
{', '.join(expected_content)}

Return:
{{
  "audience": "...",
  "product": "...",
  "angle": "...",
  "descriptors": ["...", "..."],
  "match_content": "..."
}}
"""

    payload = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful and structured tag classification assistant.",
            },
            {"role": "user", "content": prompt.strip()},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {_next_api_key()}",
        "Content-Type": "application/json",
    }

    try:
        response = _post(API_URL, headers=headers, json_payload=payload)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        result.setdefault("match_content", "unknown")
        return result
    except httpx.HTTPError as http_err:
        print("ChatGPT classification HTTP error:", http_err)
    except Exception as e:
        print("ChatGPT classification error:", e)

    return {
        "audience": "unknown",
        "product": "unknown",
        "angle": "unknown",
        "descriptors": [],
        "match_content": "unknown",
    }


async def async_chat_classify(
    labels: list[str],
    web_labels: list[str],
    expected_content=None,
    *,
    client: httpx.AsyncClient | None = None,
    max_retries: int = 3,
    backoff: float = 1.5,
) -> dict:
    """Asynchronous version of :func:`chat_classify` with basic retries."""

    expected_content = expected_content or []
    prompt = f"""
You are an ad tagging assistant. Based on the following image data:

Generic Labels:
{', '.join(labels)}

Web Entities:
{', '.join(web_labels)}

Return a JSON object with:
- "audience": describe the most likely audience (e.g., mom, teen, athlete, grandma)
- "product": name the product shown, and keep it specific if a brand is mentioned
- "angle": the emotional or marketing angle (e.g., natural beauty, wellness, performance)
- "descriptors": a short list of helpful visual or thematic descriptors (e.g., outdoors, close-up, vibrant colors)

Use the following expected content tags to set ``match_content`` to the closest tag or ``unknown`` if nothing is relevant:
{', '.join(expected_content)}

Return:
{{
  "audience": "...",
  "product": "...",
  "angle": "...",
  "descriptors": ["...", "..."],
  "match_content": "..."
}}
"""

    payload = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful and structured tag classification assistant.",
            },
            {"role": "user", "content": prompt.strip()},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }

    attempt = 0
    while True:
        try:
            headers = {
                "Authorization": f"Bearer {_next_api_key()}",
                "Content-Type": "application/json",
            }
            if client is None:
                async with httpx.AsyncClient() as c:
                    resp = await _post_async(c, API_URL, headers=headers, json_payload=payload)
            else:
                resp = await _post_async(client, API_URL, headers=headers, json_payload=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            result.setdefault("match_content", "unknown")
            return result
        except httpx.HTTPStatusError as http_err:
            status = http_err.response.status_code
            if status in {429, 500, 502, 503, 504} and attempt < max_retries:
                await asyncio.sleep(backoff * (2 ** attempt))
                attempt += 1
                continue
            print("ChatGPT classification HTTP error:", http_err)
        except Exception as e:  # pragma: no cover - defensive
            if attempt < max_retries:
                await asyncio.sleep(backoff * (2 ** attempt))
                attempt += 1
                continue
            print("ChatGPT classification error:", e)
        break

    return {
        "audience": "unknown",
        "product": "unknown",
        "angle": "unknown",
        "descriptors": [],
        "match_content": "unknown",
    }


def send_sample_message():
    """Send a sample message to GPT-4 and print the response."""
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    try:
        response = _post(API_URL, headers=headers, json_payload=payload)
        response.raise_for_status()
        data = response.json()
        print(data["choices"][0]["message"]["content"])
    except httpx.HTTPError as http_err:
        print("Sample message HTTP error:", http_err)
    except Exception as e:
        print("Sample message error:", e)


if __name__ == "__main__":
    send_sample_message()
