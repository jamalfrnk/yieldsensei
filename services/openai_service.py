from openai import OpenAI
import json
from config import OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

async def get_crypto_news():
    """Get AI-generated crypto market insights."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {
                    "role": "system",
                    "content": "You are a DeFi expert. Provide a brief summary of the "
                    "current crypto market conditions and notable events. Keep it "
                    "factual and avoid speculation or financial advice."
                },
                {
                    "role": "user",
                    "content": "What are the latest important developments in the crypto market?"
                }
            ],
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Failed to fetch crypto news: {str(e)}")
