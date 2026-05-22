import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def analyze_job_with_ai(description: str) -> str | None:
    """
    Optional LLM reasoning layer.
    Returns plain text when available, otherwise None.
    """
    if not description or len(description.strip()) < 40:
        return None

    if client is None:
        return None

    prompt = f"""
Analyze this remote job posting for legitimacy.
Return ONLY plain text (no JSON, no markdown, no bullet points) in 2-3 sentences.

Include:
1. Estimated legitimacy score out of 100.
2. Biggest red flag.
3. Strongest positive trust signal.

Job Posting:
{description[:5000]}
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful remote job legitimacy reviewer. "
                        "Keep output factual and concise."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        explanation = (response.choices[0].message.content or "").strip()
        return explanation or None
    except Exception as exc:
        print(f"AI analysis failed: {exc}")
        return None