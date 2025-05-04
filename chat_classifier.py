
import openai
import os
import json

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def chat_classify(labels, web_labels, expected_audiences, expected_products, expected_angles) -> dict:
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

Now, match each of your answers to the most relevant value in the provided expected categories below.
If there's no good match, return "unknown".

Expected audiences: {', '.join(expected_audiences)}
Expected products: {', '.join(expected_products)}
Expected angles: {', '.join(expected_angles)}

Return:
{{
  "audience": "...",
  "product": "...",
  "angle": "...",
  "descriptors": ["...", "..."],
  "match_audience": "...",
  "match_product": "...",
  "match_angle": "..."
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
        return json.loads(content)
    except Exception as e:
        print("ChatGPT classification error:", e)
        return {
            "audience": "unknown",
            "product": "unknown",
            "angle": "unknown",
            "descriptors": [],
            "match_audience": "unknown",
            "match_product": "unknown",
            "match_angle": "unknown"
        }
