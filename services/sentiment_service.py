import logging
from typing import Dict, Tuple, List
from services.coingecko_service import get_token_price, get_token_market_data

# Configure logging
logger = logging.getLogger(__name__)

def calculate_sentiment_score(
    price_change: float,
    volume_change: float,
    rsi: float,
    current_price: float,
    support_1: float,
    resistance_1: float
) -> Tuple[float, str, str]:
    """
    Calculate market sentiment score and return appropriate emoji feedback.
    Returns: (sentiment_score, sentiment_emoji, sentiment_description)
    """
    try:
        # Initialize sentiment score
        sentiment_score = 50.0  # Neutral baseline

        # Price momentum contribution (40% weight)
        if abs(price_change) > 0:
            sentiment_score += (price_change * 4)  # Amplify price impact

        # RSI contribution (30% weight)
        if rsi > 70:
            sentiment_score += 15  # Overbought
        elif rsi < 30:
            sentiment_score -= 15  # Oversold
        else:
            sentiment_score += (rsi - 50) * 0.3  # Neutral range impact

        # Support/Resistance proximity (30% weight)
        price_to_support = ((current_price - support_1) / current_price) * 100
        price_to_resistance = ((resistance_1 - current_price) / current_price) * 100

        if price_to_support < 3:  # Close to support
            sentiment_score -= 10
        elif price_to_resistance < 3:  # Close to resistance
            sentiment_score += 10

        # Normalize score to 0-100 range
        sentiment_score = max(0, min(100, sentiment_score))

        # Determine sentiment category and emoji
        sentiment_emoji, description = get_sentiment_indicators(sentiment_score)

        logger.info(f"Calculated sentiment score: {sentiment_score:.2f}, Emoji: {sentiment_emoji}")
        return sentiment_score, sentiment_emoji, description

    except Exception as e:
        logger.error(f"Error calculating sentiment: {str(e)}")
        return 50.0, "⚖️", "Neutral"

def get_sentiment_indicators(score: float) -> Tuple[str, str]:
    """
    Get appropriate emoji and description based on sentiment score.
    """
    if score >= 80:
        return "🚀", "Extremely Bullish"
    elif score >= 65:
        return "📈", "Bullish"
    elif score >= 55:
        return "😊", "Slightly Bullish"
    elif score >= 45:
        return "⚖️", "Neutral"
    elif score >= 35:
        return "😟", "Slightly Bearish"
    elif score >= 20:
        return "📉", "Bearish"
    else:
        return "🆘", "Extremely Bearish"

def get_volume_sentiment(volume_change: float) -> Tuple[str, str]:
    """
    Get volume-specific emoji and description.
    """
    if volume_change >= 100:
        return "💥", "Volume Explosion"
    elif volume_change >= 50:
        return "📊", "High Volume"
    elif volume_change >= 20:
        return "📈", "Rising Volume"
    elif volume_change <= -50:
        return "📉", "Low Volume"
    else:
        return "➡️", "Normal Volume"

# List of top tokens to track
TOP_TOKENS = ['bitcoin', 'ethereum', 'solana', 'cardano', 'ripple', 'polkadot', 'avalanche-2']

async def get_market_sentiment_data() -> List[Dict]:
    """
    Get market sentiment data for multiple tokens.
    Returns a list of dictionaries containing sentiment data for each token.
    """
    sentiment_data = []

    for token in TOP_TOKENS:
        try:
            # Get token data
            price_data = await get_token_price(token)
            market_data = await get_token_market_data(token)

            if not price_data or not market_data:
                continue

            # Calculate sentiment
            volume_change = market_data.get('total_volume_change_24h', 0)
            current_price = price_data['usd']

            # Get support and resistance from market data
            support_1 = market_data.get('low_24h', current_price * 0.95)
            resistance_1 = market_data.get('high_24h', current_price * 1.05)

            sentiment_score, sentiment_emoji, description = calculate_sentiment_score(
                price_change=price_data['usd_24h_change'],
                volume_change=volume_change,
                rsi=market_data.get('rsi', 50),
                current_price=current_price,
                support_1=support_1,
                resistance_1=resistance_1
            )

            sentiment_data.append({
                'symbol': token,
                'sentiment_score': sentiment_score,
                'emoji': sentiment_emoji,
                'description': description,
                'price_change': price_data['usd_24h_change']
            })

        except Exception as e:
            logger.error(f"Error calculating sentiment for {token}: {str(e)}")
            continue

    return sorted(sentiment_data, key=lambda x: x['sentiment_score'], reverse=True)