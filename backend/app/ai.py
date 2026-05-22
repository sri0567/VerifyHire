from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_job_with_ai(description: str):
    """
    Analyze job posting using OpenAI and return a plain text explanation
    """
    
    prompt = f"""
Analyze this remote job posting for legitimacy. Return ONLY a plain text explanation (no JSON, no formatting).

Answer these questions in 2-3 sentences:
1. How legitimate does this job seem? (score out of 100)
2. What are the red flags (if any)?
3. What are the good signs (if any)?

Job Posting:
{description[:6000]}

Return ONLY plain text, no markdown, no JSON, no bullet points.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a job scam detector. Return only plain text explanations. No JSON, no markdown, no formatting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        # Get the plain text response
        explanation = response.choices[0].message.content.strip()
        
        print(f"\n AI Analysis: {explanation[:200]}...")
        
        return explanation
        
    except Exception as e:
        print(f"❌ AI Analysis failed: {e}")
        return f"Unable to analyze job: {str(e)}"