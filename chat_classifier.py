import openai
import os
import json

openai.api_key = os.environ.get("OPENAI_API_KEY")

def chat_classify(labels: list) -> dict:
    prompt = f"""
You are an ad tagging assistant. Based on these image labels:

{', '.join(labels)}

Return a JSON object with:
- "audience": the most likely audience (e.g., mom, teen, athlete, grandma)
- "product": name the product shown, and keep it specific if a brand is mentioned
- "angle": the emotional or marketing angle (e.g., natural beauty, wellness, performance)
- "descriptors": a short list of helpful visual or thematic descriptors (e.g., outdoors, close-up, soft lighting, vibrant colors)

Only return valid JSON. No explanations. Keep keys lowercase.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful and concise image tag classifier for advertising."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.4,
        )
        content = response['choices'][0]['message']['content']
        return json.loads(content)
    except Exception as e:
        print(f"ChatGPT classification error: {e}")
        return {
            "audience": "unknown",
            "product": "unknown",
            "angle": "unknown",
            "descriptors": []
        }