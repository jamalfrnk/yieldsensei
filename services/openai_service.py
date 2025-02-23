from openai import OpenAI
import json
import logging
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI service with proper error handling"""
        try:
            self.client = OpenAI(api_key=api_key) if api_key else None
            if not self.client:
                logger.warning("OpenAI client not initialized - API key missing")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            self.client = None

    def get_crypto_news(self) -> str:
        """Get crypto market news and insights"""
        try:
            if not self.client:
                return "OpenAI integration not available. Using default market analysis."

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a DeFi expert providing concise crypto market updates. "
                            "Focus on these key areas:\n"
                            "1. Market Overview (major cryptocurrencies)\n"
                            "2. Notable DeFi Protocol Updates\n"
                            "3. Important Market Events\n\n"
                            "Keep it factual, avoid speculation or financial advice. "
                            "Use markdown formatting and emojis for better readability."
                        )
                    },
                    {
                        "role": "user",
                        "content": "What are the latest important developments in the crypto market?"
                    }
                ],
                max_tokens=400
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to fetch crypto news: {str(e)}")
            return "Market insights temporarily unavailable. Please try again later."

    def process_nlp_query(self, query: str) -> str:
        """Process natural language queries about crypto markets"""
        try:
            if not self.client:
                return "OpenAI integration not available. Please try basic commands."

            response = self.client.chat.completions.create(
                model="gpt-4",
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
            logger.error(f"Failed to process query: {str(e)}")
            return f"Sorry, I encountered an error processing your query. Please try again later."

# Create singleton instance
_openai_service = None

def init_openai_service(api_key: Optional[str] = None) -> None:
    """Initialize the OpenAI service singleton"""
    global _openai_service
    _openai_service = OpenAIService(api_key)

def get_crypto_news_sync() -> str:
    """Synchronous wrapper for get_crypto_news"""
    global _openai_service
    if not _openai_service:
        logger.warning("OpenAI service not initialized, initializing with default settings")
        init_openai_service()
    return _openai_service.get_crypto_news()

def process_nlp_query_sync(query: str) -> str:
    """Synchronous wrapper for process_nlp_query"""
    global _openai_service
    if not _openai_service:
        logger.warning("OpenAI service not initialized, initializing with default settings")
        init_openai_service()
    return _openai_service.process_nlp_query(query)

# Keep async versions for backward compatibility
async def get_crypto_news():
    return get_crypto_news_sync()

async def process_nlp_query(query: str):
    return process_nlp_query_sync(query)