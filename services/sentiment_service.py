import logging
from typing import Dict, Tuple, List
from services.coingecko_service import get_token_price, get_token_market_data
from services.technical_analysis import calculate_rsi  # Fix import
import aiohttp
import asyncio
from datetime import datetime, timedelta
from cachetools import TTLCache

# Configure logging
logger = logging.getLogger(__name__)

# Cache for storing API responses (2 minutes TTL)
market_data_cache = TTLCache(maxsize=100, ttl=120)
token_cache = TTLCache(maxsize=20, ttl=300)  # 5 minutes for top tokens

async def get_top_20_tokens() -> List[str]:
    """
    Fetch top 20 cryptocurrencies by market cap from CoinGecko.
    Returns list of token ids.
    """
    cache_key = 'top_tokens'
    if cache_key in token_cache:
        return token_cache[cache_key]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.coingecko.com/api/v3/coins/markets',
                params={
                    'vs_currency': 'usd',
                    'order': 'market_cap_desc',
                    'per_page': 20,
                    'page': 1,
                    'sparkline': False
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    top_tokens = [coin['id'] for coin in data]
                    token_cache[cache_key] = top_tokens
                    return top_tokens
                else:
                    logger.error(f"Failed to fetch top tokens: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Error fetching top tokens: {str(e)}")
        return []

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

async def get_market_sentiment_data() -> List[Dict]:
    """
    Get market sentiment data for top 20 cryptocurrencies.
    Returns a list of dictionaries containing sentiment data for each token.
    """
    sentiment_data = []

    # Fetch top 20 tokens
    top_tokens = await get_top_20_tokens()
    if not top_tokens:
        logger.error("Failed to fetch top tokens, using fallback list")
        top_tokens = ['bitcoin', 'ethereum', 'solana', 'cardano', 'ripple']  # Fallback list

    logger.info(f"Processing sentiment for {len(top_tokens)} tokens")

    # Process tokens with rate limiting
    for token in top_tokens:
        try:
            logger.info(f"Fetching data for token: {token}")

            # Check cache first
            cache_key = f"sentiment_{token}"
            if cache_key in market_data_cache:
                sentiment_data.append(market_data_cache[cache_key])
                continue

            # Get token data with delay to respect rate limits
            await asyncio.sleep(0.5)  # 500ms delay between requests

            price_data = await get_token_price(token)
            if not price_data:
                logger.warning(f"No price data available for {token}")
                continue

            market_data = await get_token_market_data(token)
            if not market_data:
                logger.warning(f"No market data available for {token}")
                continue

            # Calculate sentiment
            volume_change = market_data.get('total_volume_change_24h', 0)
            current_price = price_data['usd']
            price_change = price_data.get('usd_24h_change', 0)

            # Get support and resistance from market data
            support_1 = market_data.get('low_24h', current_price * 0.95)
            resistance_1 = market_data.get('high_24h', current_price * 1.05)

            # Calculate RSI
            rsi_value = 50  # Default neutral value
            if 'prices' in market_data:
                prices = [price[1] for price in market_data['prices'][-14:]]
                if len(prices) >= 14:
                    rsi_value = calculate_rsi(prices)

            sentiment_score, sentiment_emoji, description = calculate_sentiment_score(
                price_change=price_change,
                volume_change=volume_change,
                rsi=rsi_value,
                current_price=current_price,
                support_1=support_1,
                resistance_1=resistance_1
            )

            token_data = {
                'symbol': token,
                'sentiment_score': sentiment_score,
                'emoji': sentiment_emoji,
                'description': description,
                'price_change': price_change
            }

            # Cache the result
            market_data_cache[cache_key] = token_data
            sentiment_data.append(token_data)

            logger.info(f"Calculated sentiment for {token}: Score={sentiment_score}, Description={description}")

        except Exception as e:
            logger.error(f"Error calculating sentiment for {token}: {str(e)}")
            continue

    # Sort by sentiment score in descending order
    sorted_data = sorted(sentiment_data, key=lambda x: x['sentiment_score'], reverse=True)
    logger.info(f"Successfully processed {len(sorted_data)} tokens")
    return sorted_data