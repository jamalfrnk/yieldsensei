import aiohttp
import asyncio
import logging
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

# Configure logging
logger = logging.getLogger(__name__)

# BirdEye API configurations
BIRDEYE_API_KEY = os.environ.get('BIRDEYE_API_KEY', 'a2f6b375cc2c4afbb5fdb456d7bdc4ff')
BIRDEYE_BASE_URL = "https://public-api.birdeye.so"

# Token mapping for common symbols
TOKEN_MAP = {
    'btc': 'bitcoin',
    'BTC': 'bitcoin',
    'eth': 'ethereum',
    'ETH': 'ethereum',
    'sol': 'solana',
    'SOL': 'solana',
    'bnb': 'binancecoin',
    'BNB': 'binancecoin',
    'ada': 'cardano',
    'ADA': 'cardano',
    'dot': 'polkadot',
    'DOT': 'polkadot',
    'doge': 'dogecoin',
    'DOGE': 'dogecoin',
    'xrp': 'ripple',
    'XRP': 'ripple',
    'avax': 'avalanche-2',
    'AVAX': 'avalanche-2',
    'matic': 'matic-network',
    'MATIC': 'matic-network',
}

# Mapping from token name to BirdEye token address
TOKEN_ADDRESS_MAP = {
    'bitcoin': 'So11111111111111111111111111111111111111112',  # Using SOL as placeholder
    'ethereum': 'So11111111111111111111111111111111111111112',  # Using SOL as placeholder
    'solana': 'So11111111111111111111111111111111111111112',
    'binancecoin': 'So11111111111111111111111111111111111111112',  # Using SOL as placeholder
    'cardano': 'So11111111111111111111111111111111111111112',  # Using SOL as placeholder
    'polkadot': 'So11111111111111111111111111111111111111112',  # Using SOL as placeholder
    'dogecoin': 'So11111111111111111111111111111111111111112',  # Using SOL as placeholder
    'ripple': 'So11111111111111111111111111111111111111112',  # Using SOL as placeholder
    'avalanche-2': 'So11111111111111111111111111111111111111112',  # Using SOL as placeholder
    'matic-network': 'So11111111111111111111111111111111111111112',  # Using SOL as placeholder
}

# Reverse mapping to get token name from address
ADDRESS_TO_TOKEN = {v: k for k, v in TOKEN_ADDRESS_MAP.items()}

async def retry_with_backoff(func, *args, max_retries=5, **kwargs):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1.5  # Exponential backoff
                logger.warning(f"API call failed, retrying in {wait_time} seconds: {str(e)}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All retries failed: {str(e)}")
                raise

async def get_token_price(input_token: str) -> Dict:
    """Fetch token price data from BirdEye API."""
    token_id = normalize_token_id(input_token)
    token_address = TOKEN_ADDRESS_MAP.get(token_id)

    if not token_address:
        logger.error(f"No address mapping for token: {input_token}")
        return {
            "usd": 0.0,
            "usd_24h_change": 0.0
        }

    async def _fetch_token_price(address: str):
        headers = {"X-API-KEY": BIRDEYE_API_KEY}
        url = f"{BIRDEYE_BASE_URL}/defi/price"
        params = {"address": address}

        async with aiohttp.ClientSession() as session:
            try:
                logger.info(f"Fetching price data for token address: {address}")
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 429:
                        logger.error("Rate limit exceeded")
                        raise Exception("Rate limit exceeded")

                    response.raise_for_status()
                    data = await response.json()

                    if data.get('success') != True:
                        error_msg = data.get('message', 'Unknown error')
                        logger.error(f"API error: {error_msg}")
                        raise Exception(f"API error: {error_msg}")

                    price_data = data.get('data', {})
                    if not price_data:
                        raise Exception("No price data received")

                    # Calculate 24h change
                    current_price = float(price_data.get('value', 0))
                    price_24h_ago = float(price_data.get('value24h', current_price))

                    if price_24h_ago > 0:
                        change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
                    else:
                        change_24h = 0

                    return {
                        "usd": current_price,
                        "usd_24h_change": change_24h
                    }

            except aiohttp.ClientError as e:
                logger.error(f"API request failed: {str(e)}")
                raise Exception(f"Failed to fetch price data: {str(e)}")

    return await retry_with_backoff(_fetch_token_price, token_address)

async def get_token_market_data(input_token: str) -> Dict:
    """Fetch detailed market data including historical prices from BirdEye API."""
    token_id = normalize_token_id(input_token)
    token_address = TOKEN_ADDRESS_MAP.get(token_id)

    if not token_address:
        logger.error(f"No address mapping for token: {input_token}")
        return default_market_data()

    async def _fetch_market_data(address: str):
        headers = {"X-API-KEY": BIRDEYE_API_KEY}

        # Get current price data
        price_url = f"{BIRDEYE_BASE_URL}/defi/price"
        price_params = {"address": address}

        # Get token metadata
        metadata_url = f"{BIRDEYE_BASE_URL}/public/tokenlist"
        metadata_params = {"address": address}

        # Get historical price data
        ohlcv_url = f"{BIRDEYE_BASE_URL}/defi/candles"
        ohlcv_params = {
            "address": address,
            "type": "1H",  # 1 hour interval
            "limit": 168  # 7 days (24 * 7)
        }

        async with aiohttp.ClientSession() as session:
            try:
                # Fetch data concurrently
                tasks = [
                    session.get(price_url, params=price_params, headers=headers),
                    session.get(metadata_url, params=metadata_params, headers=headers),
                    session.get(ohlcv_url, params=ohlcv_params, headers=headers)
                ]

                responses = await asyncio.gather(*tasks)
                for response in responses:
                    response.raise_for_status()

                # Process responses
                price_data = await responses[0].json()
                metadata = await responses[1].json()
                ohlcv_data = await responses[2].json()

                # Extract price info
                price_info = price_data.get('data', {})
                current_price = float(price_info.get('value', 0))

                # Extract metadata
                token_meta = metadata.get('data', {})
                supply = float(token_meta.get('supply', 0))
                symbol = token_meta.get('symbol', input_token.upper())

                # Extract OHLCV data
                candles = ohlcv_data.get('data', [])

                # Calculate market cap
                market_cap = current_price * supply

                # Calculate 24h volume from candles
                volume_24h = sum(float(candle.get('volume', 0)) for candle in candles[:24]) if len(candles) >= 24 else 0

                # Calculate 24h high/low
                if candles:
                    high_24h = max(float(candle.get('high', 0)) for candle in candles[:24]) if len(candles) >= 24 else current_price
                    low_24h = min(float(candle.get('low', 0)) for candle in candles[:24]) if len(candles) >= 24 else current_price
                else:
                    high_24h = low_24h = current_price

                # Calculate price change
                price_24h_ago = float(price_info.get('value24h', current_price))
                if price_24h_ago > 0:
                    price_change_percentage_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
                else:
                    price_change_percentage_24h = 0

                # Format historical price data
                prices = []
                for candle in candles:
                    timestamp = int(candle.get('timestamp', 0))
                    close_price = float(candle.get('close', 0))
                    prices.append([timestamp, close_price])

                return {
                    "market_cap": market_cap,
                    "total_volume": volume_24h,
                    "high_24h": high_24h,
                    "low_24h": low_24h,
                    "price_change_percentage_24h": price_change_percentage_24h,
                    "market_cap_rank": 0,  # Not available in BirdEye
                    "prices": prices
                }

            except aiohttp.ClientError as e:
                logger.error(f"API request failed: {str(e)}")
                raise Exception(f"Failed to fetch market data: {str(e)}")
            except (KeyError, ValueError) as e:
                logger.error(f"Data parsing error: {str(e)}")
                raise Exception(f"Failed to parse market data: {str(e)}")

    return await retry_with_backoff(_fetch_market_data, token_address)

def normalize_token_id(input_token: str) -> str:
    """Normalize token ID and apply mapping."""
    token_id = input_token.lower().strip()
    return TOKEN_MAP.get(token_id, token_id)

def default_market_data() -> Dict:
    """Return default market data when API fails."""
    return {
        "market_cap": 0,
        "total_volume": 0,
        "high_24h": 0,
        "low_24h": 0,
        "price_change_percentage_24h": 0,
        "market_cap_rank": 0,
        "prices": []
    }

async def get_historical_data_async(coin_id: str, days: int = 90) -> pd.DataFrame:
    """Fetch historical price data and return as DataFrame."""
    token_id = normalize_token_id(coin_id)
    token_address = TOKEN_ADDRESS_MAP.get(token_id)

    if not token_address:
        logger.error(f"No address mapping for token: {coin_id}")
        return pd.DataFrame()

    # Determine appropriate interval based on requested days
    if days <= 1:
        interval = "5m"  # 5 minutes
        limit = 288      # 24 hours (12 * 24)
    elif days <= 7:
        interval = "1h"  # 1 hour
        limit = days * 24
    elif days <= 30:
        interval = "4h"  # 4 hours
        limit = days * 6
    elif days <= 90:
        interval = "1d"  # 1 day
        limit = days
    else:
        interval = "1d"  # 1 day
        limit = min(days, 365)  # Cap at 365 days

    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    ohlcv_url = f"{BIRDEYE_BASE_URL}/defi/candles"
    ohlcv_params = {
        "address": token_address,
        "type": interval,
        "limit": limit
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ohlcv_url, params=ohlcv_params, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get('success') != True:
                    logger.error(f"API error: {data.get('message', 'Unknown error')}")
                    return pd.DataFrame()

                candles = data.get('data', [])
                if not candles:
                    logger.warning(f"No historical data available for {coin_id}")
                    return pd.DataFrame()

                # Convert to DataFrame
                df_data = []
                for candle in candles:
                    timestamp = int(candle.get('timestamp', 0))
                    close_price = float(candle.get('close', 0))
                    df_data.append({
                        'timestamp': pd.to_datetime(timestamp, unit='ms'),
                        'price': close_price
                    })

                df = pd.DataFrame(df_data)
                if not df.empty:
                    df.set_index('timestamp', inplace=True)
                    df.sort_index(inplace=True)

                return df

    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        return pd.DataFrame()

def get_historical_data(coin_id: str, days: int = 90) -> pd.DataFrame:
    """Synchronous wrapper for get_historical_data_async."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(get_historical_data_async(coin_id, days))

# Export key functions
__all__ = ['get_token_price', 'get_token_market_data', 'get_historical_data']