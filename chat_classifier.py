
import openai
import os
import json

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful and structured tag classification assistant."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.4,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        # Older prompts may omit the optional match_content field
        data.setdefault("match_content", "unknown")
        return data
    except Exception as e:
        print("ChatGPT classification error:", e)
        return {
            "audience": "unknown",
            "product": "unknown",
            "angle": "unknown",
            "descriptors": [],
            "match_content": "unknown",
        }
