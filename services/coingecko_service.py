import aiohttp
import asyncio
from config import COINGECKO_BASE_URL, ERROR_INVALID_TOKEN
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

# Get API key from environment
COINGECKO_API_KEY = os.environ.get('COINGECKO_API_KEY')
BASE_URL = "https://pro-api.coingecko.com/api/v3" if COINGECKO_API_KEY else COINGECKO_BASE_URL

from time import sleep
from functools import wraps
import time

def rate_limit_decorator(calls_per_minute=30):
    min_interval = 60.0 / calls_per_minute
    last_call_time = {}
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            key = func.__name__
            if key in last_call_time:
                time_since_last_call = now - last_call_time[key]
                if time_since_last_call < min_interval:
                    sleep_time = min_interval - time_since_last_call
                    await asyncio.sleep(sleep_time)
            last_call_time[key] = time.time()
            return await func(*args, **kwargs)
        return wrapper
    return decorator

async def retry_with_backoff(func, *args, max_retries=5):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func(*args)
        except Exception as e:
            if ("429" in str(e) or "rate limit" in str(e).lower()) and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 3  # Exponential backoff: 3, 6, 12, 24, 48 seconds
                logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry")
                await asyncio.sleep(wait_time)
                continue
            elif attempt < max_retries - 1:
                wait_time = 2  # Brief pause for non-rate-limit errors
                await asyncio.sleep(wait_time)
                continue
            raise

async def get_token_price(input_token: str):
    """Fetch token price data from CoinGecko API."""
    async def _fetch_price(token_id: str):
        headers = {"x-cg-pro-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}

        async with aiohttp.ClientSession() as session:
            try:
                logger.info(f"Fetching price data for token: {token_id}")
                url = f"{BASE_URL}/simple/price"
                params = {
                    "ids": token_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true"
                }

                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 404:
                        logger.error(f"Token not found: {token_id}")
                        raise ValueError(ERROR_INVALID_TOKEN)
                    elif response.status == 429:
                        logger.error("Rate limit exceeded")
                        raise Exception("Rate limit exceeded. Please try again later.")
                    elif response.status == 403:
                        logger.error("Invalid API key or unauthorized access")
                        raise Exception("API authentication failed. Please check your API key.")

                    data = await response.json()
                    logger.info(f"Received response: {data}")

                    if isinstance(data, dict) and 'status' in data and 'error_code' in data['status']:
                        if data['status']['error_code'] == 429:
                            raise Exception("Rate limit exceeded")
                        raise ValueError(data['status'].get('error_message', ERROR_INVALID_TOKEN))

                    if token_id not in data:
                        logger.error(f"Token {token_id} not in response data")
                        raise ValueError(ERROR_INVALID_TOKEN)

                    return {
                        "usd": data[token_id]["usd"],
                        "usd_24h_change": data[token_id]["usd_24h_change"]
                    }
            except aiohttp.ClientError as e:
                logger.error(f"API request failed: {str(e)}")
                raise Exception(f"Failed to fetch price data: {str(e)}")

    # Normalize token ID and apply mapping
    token_id = input_token.lower().strip()
    token_map = {
        'btc': 'bitcoin',
        'eth': 'ethereum',
        'sol': 'solana',
        'bnb': 'binancecoin',
        'ada': 'cardano',
        'dot': 'polkadot',
        'doge': 'dogecoin',
        'xrp': 'ripple',
        'avax': 'avalanche-2',
        'matic': 'matic-network',
    }

    if token_id in token_map:
        token_id = token_map[token_id]

    return await retry_with_backoff(_fetch_price, token_id)

async def get_token_market_data(input_token: str):
    """Fetch detailed market data including historical prices from CoinGecko API."""
    async def _fetch_market_data(token_id: str):
        headers = {"x-cg-pro-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}

        async with aiohttp.ClientSession() as session:
            try:
                logger.info(f"Fetching market data for token: {token_id}")

                # Get current market data
                url = f"{BASE_URL}/coins/{token_id}"
                params = {
                    "localization": "false",
                    "tickers": "false",
                    "community_data": "false",
                    "developer_data": "false",
                    "sparkline": "false"
                }

                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 404:
                        logger.error(f"Token not found: {token_id}")
                        raise ValueError(ERROR_INVALID_TOKEN)
                    elif response.status == 429:
                        logger.error("Rate limit exceeded")
                        raise Exception("Rate limit exceeded")
                    elif response.status == 403:
                        logger.error("Invalid API key or unauthorized access")
                        raise Exception("API authentication failed. Please check your API key.")

                    data = await response.json()

                    # Check for error response
                    if isinstance(data, dict) and 'status' in data and 'error_code' in data['status']:
                        if data['status']['error_code'] == 429:
                            raise Exception("Rate limit exceeded")
                        raise ValueError(data['status'].get('error_message', ERROR_INVALID_TOKEN))

                    market_data = data["market_data"]

                # Get historical price data
                history_url = f"{BASE_URL}/coins/{token_id}/market_chart"
                history_params = {
                    "vs_currency": "usd",
                    "days": "365",
                    "interval": "daily"
                }

                async with session.get(history_url, params=history_params, headers=headers) as history_response:
                    if history_response.status == 404:
                        logger.error(f"Historical data not found for token: {token_id}")
                        raise ValueError(ERROR_INVALID_TOKEN)
                    elif history_response.status == 429:
                        logger.error("Rate limit exceeded")
                        raise Exception("Rate limit exceeded")

                    history_data = await history_response.json()

                    if not history_data or "prices" not in history_data:
                        logger.error("No price data in historical response")
                        raise ValueError("No historical price data available")

                    return {
                        "market_cap": market_data["market_cap"]["usd"],
                        "total_volume": market_data["total_volume"]["usd"],
                        "high_24h": market_data["high_24h"]["usd"],
                        "low_24h": market_data["low_24h"]["usd"],
                        "price_change_percentage_24h": market_data["price_change_percentage_24h"],
                        "market_cap_rank": data["market_cap_rank"],
                        "prices": history_data["prices"]
                    }

            except aiohttp.ClientError as e:
                logger.error(f"API request failed: {str(e)}")
                raise Exception(f"Failed to fetch market data: {str(e)}")
            except KeyError as e:
                logger.error(f"Invalid market data format: {str(e)}")
                raise Exception(f"Invalid market data format: {str(e)}")

    # Normalize token ID and apply mapping
    token_id = input_token.lower().strip()
    token_map = {
        'btc': 'bitcoin',
        'eth': 'ethereum',
        'sol': 'solana',
        'bnb': 'binancecoin',
        'ada': 'cardano',
        'dot': 'polkadot',
        'doge': 'dogecoin',
        'xrp': 'ripple',
        'avax': 'avalanche-2',
        'matic': 'matic-network',
    }

    if token_id in token_map:
        token_id = token_map[token_id]

    return await retry_with_backoff(_fetch_market_data, token_id)