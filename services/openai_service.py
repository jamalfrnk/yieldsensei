from openai import OpenAI
import json
from config import OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def get_crypto_news():
    """Get AI-generated crypto market insights."""
    if not client:
        return "OpenAI API key not configured. Please contact the bot administrator."

    try:
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
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
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        content = json.loads(response.choices[0].message.content)
        return content.get("summary", "Unable to generate market insights.")
    except Exception as e:
        return f"Failed to fetch crypto news: {str(e)}"

async def process_nlp_query(query: str):
    """Process natural language queries about crypto and DeFi."""
    if not client:
        return "OpenAI API key not configured. Please contact the bot administrator."

    try:
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Yield Sensei, an AI-powered DeFi assistant. "
                        "Provide helpful, educational responses about cryptocurrency, "
                        "DeFi protocols, and blockchain technology. Follow these rules:\n"
                        "1. Never provide financial advice or price predictions\n"
                        "2. Focus on education and explaining concepts\n"
                        "3. Keep responses concise and clear\n"
                        "4. Use emojis appropriately to make responses engaging\n"
                        "5. Always recommend DYOR (Do Your Own Research)\n"
                        "6. If unsure, acknowledge limitations and suggest reliable resources\n\n"
                        "Format your response as a JSON object with 'message' key containing "
                        "the formatted response text."
                    )
                },
                {"role": "user", "content": query}
            ],
            max_tokens=500,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = json.loads(response.choices[0].message.content)
        return content.get("message", "I apologize, but I couldn't process your query properly. Please try again.")
    except Exception as e:
        return f"Failed to process your query: {str(e)}"