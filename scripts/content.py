"""
content.py — generate PDF guide content via Groq (free, Llama 3).
Produces structured sections: intro, 5 chapters, conclusion, tips.
"""

import os
import json
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are an expert guide writer. Write clear, practical,
engaging content that provides real value. Use simple language that works
for a global audience. Be specific and actionable, not generic."""

CONTENT_SCHEMA = """
Return JSON only, no markdown fences. Schema:
{
  "title": "Complete Guide: <topic>",
  "subtitle": "one compelling sentence",
  "intro": "150-word introduction",
  "chapters": [
    {"heading": "chapter title", "body": "300-word chapter content"},
    ... (5 chapters total)
  ],
  "tips": ["tip 1", "tip 2", "tip 3", "tip 4", "tip 5"],
  "conclusion": "100-word conclusion",
  "tags": ["tag1", "tag2", "tag3"]
}
"""


def generate_content(topic: str, country: str) -> dict:
    """
    Call Groq (Llama 3.3 70B, free tier) to generate full guide content.
    Returns parsed dict matching CONTENT_SCHEMA.
    """
    prompt = f"""Write a complete, practical guide about: "{topic}"
Target audience: people in {country} interested in this topic.
Make it valuable, specific, and actionable.

{CONTENT_SCHEMA}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # free on Groq
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.7,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


def generate_description(content: dict) -> str:
    """Short Gumroad product description from content dict."""
    tags = " · ".join(f"#{t}" for t in content.get("tags", []))
    return (
        f"{content['subtitle']}\n\n"
        f"What's inside:\n"
        + "\n".join(f"• {c['heading']}" for c in content["chapters"])
        + f"\n\n{tags}"
    )


if __name__ == "__main__":
    result = generate_content("AI tools for small business", "US")
    print(result["title"])
    print(f"Chapters: {len(result['chapters'])}")
