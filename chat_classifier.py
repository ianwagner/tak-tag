
import os
import json
import httpx

API_URL = "https://api.openai.com/v1/chat/completions"

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

    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
        "Content-Type": "application/json",
    }
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

    try:
        response = httpx.post(API_URL, headers=headers, json=payload, timeout=30)
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
        response = httpx.post(API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(data["choices"][0]["message"]["content"])
    except httpx.HTTPError as http_err:
        print("Sample message HTTP error:", http_err)
    except Exception as e:
        print("Sample message error:", e)


if __name__ == "__main__":
    send_sample_message()
