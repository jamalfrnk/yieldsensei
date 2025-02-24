import logging
from typing import Tuple
from services.coingecko_service import get_token_price

# Configure logging
logger = logging.getLogger(__name__)

def calculate_sentiment_score(price_change: float) -> Tuple[float, str]:
    """
    Calculate basic market sentiment score and return appropriate emoji.
    Returns: (sentiment_score, sentiment_emoji)
    """
    try:
        # Initialize sentiment score
        sentiment_score = 50.0  # Neutral baseline

        # Price momentum contribution
        if abs(price_change) > 0:
            sentiment_score += (price_change * 5)  # Price impact

        # Normalize score to 0-100 range
        sentiment_score = max(0, min(100, sentiment_score))

        # Get appropriate emoji
        sentiment_emoji = get_sentiment_emoji(sentiment_score)

        logger.info(f"Calculated sentiment score: {sentiment_score:.2f}")
        return sentiment_score, sentiment_emoji

    except Exception as e:
        logger.error(f"Error calculating sentiment: {str(e)}")
        return 50.0, "⚖️"

def get_sentiment_emoji(score: float) -> str:
    """Get appropriate emoji based on sentiment score."""
    if score >= 75:
        return "🚀"
    elif score >= 60:
        return "📈"
    elif score >= 40:
        return "⚖️"
    elif score >= 25:
        return "📉"
    else:
        return "🆘"