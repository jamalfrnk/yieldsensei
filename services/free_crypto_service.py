
import aiohttp
import asyncio
import logging
import pandas as pd
import numpy as np
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import yfinance as yf

# Configure logging
logger = logging.getLogger(__name__)

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

# Mapping to Yahoo Finance tickers
YAHOO_TICKER_MAP = {
    'bitcoin': 'BTC-USD',
    'ethereum': 'ETH-USD',
    'solana': 'SOL-USD',
    'binancecoin': 'BNB-USD',
    'cardano': 'ADA-USD',
    'polkadot': 'DOT-USD',
    'dogecoin': 'DOGE-USD',
    'ripple': 'XRP-USD',
    'avalanche-2': 'AVAX-USD',
    'matic-network': 'MATIC-USD',
}

# CoinGecko base URL
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Last request timestamps to implement rate limiting
last_requests = {
    'coingecko': 0,
    'yahoo': 0
}

def normalize_token_id(input_token: str) -> str:
    """Normalize token ID and apply mapping."""
    token_id = input_token.lower().strip()
    return TOKEN_MAP.get(token_id, token_id)

async def rate_limited_request(source: str, min_interval: float = 1.5):
    """Rate limit requests to prevent hitting API limits."""
    current_time = time.time()
    time_since_last = current_time - last_requests.get(source, 0)
    
    if time_since_last < min_interval:
        # Add jitter to avoid synchronized requests
        delay = min_interval - time_since_last + (random.random() * 0.5)
        await asyncio.sleep(delay)
    
    last_requests[source] = time.time()

async def get_token_price(input_token: str) -> Dict:
    """Fetch token price data from CoinGecko API."""
    token_id = normalize_token_id(input_token)
    
    try:
        # Apply rate limiting
        await rate_limited_request('coingecko')
        
        async with aiohttp.ClientSession() as session:
            logger.info(f"Fetching price data for token: {token_id}")
            url = f"{COINGECKO_BASE_URL}/simple/price"
            params = {
                "ids": token_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 404:
                    logger.error(f"Token not found: {token_id}")
                    return {"usd": 0.0, "usd_24h_change": 0.0}
                elif response.status == 429:
                    logger.error("Rate limit exceeded, using backup data source")
                    return await get_price_from_yahoo(token_id)
                
                data = await response.json()
                
                if token_id not in data:
                    logger.error(f"Token {token_id} not in response data")
                    return {"usd": 0.0, "usd_24h_change": 0.0}
                
                return {
                    "usd": data[token_id].get("usd", 0),
                    "usd_24h_change": data[token_id].get("usd_24h_change", 0)
                }
    except Exception as e:
        logger.error(f"Error fetching price from CoinGecko: {str(e)}")
        # Fallback to Yahoo Finance
        return await get_price_from_yahoo(token_id)

async def get_price_from_yahoo(token_id: str) -> Dict:
    """Fallback method to get price from Yahoo Finance."""
    try:
        await rate_limited_request('yahoo')
        yahoo_ticker = YAHOO_TICKER_MAP.get(token_id)
        
        if not yahoo_ticker:
            logger.error(f"No Yahoo ticker for {token_id}")
            return {"usd": 0.0, "usd_24h_change": 0.0}
        
        # Use run_in_executor since yfinance is synchronous
        loop = asyncio.get_running_loop()
        ticker = await loop.run_in_executor(None, lambda: yf.Ticker(yahoo_ticker))
        
        # Get current data
        current_data = await loop.run_in_executor(None, lambda: ticker.history(period="2d"))
        
        if current_data.empty:
            return {"usd": 0.0, "usd_24h_change": 0.0}
        
        current_price = current_data['Close'].iloc[-1]
        
        # Calculate 24h change
        if len(current_data) >= 2:
            prev_price = current_data['Close'].iloc[-2]
            change_24h = ((current_price - prev_price) / prev_price) * 100
        else:
            change_24h = 0
        
        return {
            "usd": current_price,
            "usd_24h_change": change_24h
        }
    except Exception as e:
        logger.error(f"Error fetching price from Yahoo: {str(e)}")
        return {"usd": 0.0, "usd_24h_change": 0.0}

async def get_token_market_data(input_token: str) -> Dict:
    """Fetch detailed market data including historical prices."""
    token_id = normalize_token_id(input_token)
    
    try:
        # Apply rate limiting
        await rate_limited_request('coingecko')
        
        async with aiohttp.ClientSession() as session:
            logger.info(f"Fetching market data for token: {token_id}")
            
            url = f"{COINGECKO_BASE_URL}/coins/{token_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false"
            }
            
            async with session.get(url, params=params) as response:
                if response.status in (404, 429):
                    logger.error(f"CoinGecko API error: {response.status}")
                    # Fallback to Yahoo Finance
                    return await get_market_data_from_yahoo(token_id)
                
                data = await response.json()
                market_data = data.get("market_data", {})
                
                # Get historical price data for chart
                hist_url = f"{COINGECKO_BASE_URL}/coins/{token_id}/market_chart"
                hist_params = {
                    "vs_currency": "usd",
                    "days": "90",
                    "interval": "daily"
                }
                
                async with session.get(hist_url, params=hist_params) as hist_response:
                    if hist_response.status in (404, 429):
                        logger.error(f"Error fetching historical data: {hist_response.status}")
                        prices = []
                    else:
                        history_data = await hist_response.json()
                        prices = history_data.get("prices", [])
                
                return {
                    "market_cap": market_data.get("market_cap", {}).get("usd", 0),
                    "total_volume": market_data.get("total_volume", {}).get("usd", 0),
                    "high_24h": market_data.get("high_24h", {}).get("usd", 0),
                    "low_24h": market_data.get("low_24h", {}).get("usd", 0),
                    "price_change_percentage_24h": market_data.get("price_change_percentage_24h", 0),
                    "market_cap_rank": data.get("market_cap_rank", 0),
                    "prices": prices
                }
    except Exception as e:
        logger.error(f"Error fetching market data from CoinGecko: {str(e)}")
        # Fallback to Yahoo Finance
        return await get_market_data_from_yahoo(token_id)

async def get_market_data_from_yahoo(token_id: str) -> Dict:
    """Fallback method to get market data from Yahoo Finance."""
    try:
        await rate_limited_request('yahoo')
        yahoo_ticker = YAHOO_TICKER_MAP.get(token_id)
        
        if not yahoo_ticker:
            logger.error(f"No Yahoo ticker for {token_id}")
            return default_market_data()
        
        # Use run_in_executor since yfinance is synchronous
        loop = asyncio.get_running_loop()
        ticker = await loop.run_in_executor(None, lambda: yf.Ticker(yahoo_ticker))
        
        # Get price history
        history = await loop.run_in_executor(None, lambda: ticker.history(period="90d"))
        
        if history.empty:
            return default_market_data()
        
        # Get info
        info = ticker.info
        
        # Calculate market data
        current_price = history['Close'].iloc[-1]
        high_24h = history['High'].iloc[-1]
        low_24h = history['Low'].iloc[-1]
        
        # Calculate 24h change
        if len(history) >= 2:
            prev_price = history['Close'].iloc[-2]
            price_change = ((current_price - prev_price) / prev_price) * 100
        else:
            price_change = 0
        
        # Format historical price data for Chart.js
        prices = []
        for date, row in history.iterrows():
            timestamp = int(date.timestamp() * 1000)
            prices.append([timestamp, row['Close']])
        
        return {
            "market_cap": info.get('marketCap', 0),
            "total_volume": info.get('volume', 0) * current_price,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "price_change_percentage_24h": price_change,
            "market_cap_rank": 0,  # Not available in Yahoo Finance
            "prices": prices
        }
    except Exception as e:
        logger.error(f"Error fetching market data from Yahoo: {str(e)}")
        return default_market_data()

def default_market_data() -> Dict:
    """Return default market data."""
    return {
        "market_cap": 0,
        "total_volume": 0,
        "high_24h": 0,
        "low_24h": 0,
        "price_change_percentage_24h": 0,
        "market_cap_rank": 0,
        "prices": []
    }

def get_historical_data(coin_id: str, days: int = 90) -> pd.DataFrame:
    """Fetch historical price data and return as DataFrame."""
    try:
        token_id = normalize_token_id(coin_id)
        yahoo_ticker = YAHOO_TICKER_MAP.get(token_id)
        
        if not yahoo_ticker:
            logger.error(f"No Yahoo ticker for {token_id}")
            return pd.DataFrame()
        
        # Fetch data from Yahoo Finance (more reliable for historical data)
        if days <= 1:
            period = "1d"
            interval = "5m"
        elif days <= 7:
            period = "7d"
            interval = "1h"
        elif days <= 30:
            period = "1mo"
            interval = "1d"
        elif days <= 90:
            period = "3mo"
            interval = "1d"
        else:
            period = "1y"
            interval = "1d"
        
        ticker = yf.Ticker(yahoo_ticker)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            logger.warning(f"No historical data available for {coin_id}")
            return pd.DataFrame()
        
        # Create DataFrame with expected format
        result_df = pd.DataFrame(index=df.index)
        result_df['price'] = df['Close']
        
        return result_df
    
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        # Try CoinGecko as fallback
        return get_historical_data_from_coingecko(coin_id, days)

def get_historical_data_from_coingecko(coin_id: str, days: int = 90) -> pd.DataFrame:
    """Fallback method to get historical data from CoinGecko."""
    try:
        # Implement rate limiting
        time.sleep(1.5)  # Ensure we don't hit rate limits
        
        token_id = normalize_token_id(coin_id)
        
        # Synchronous request to CoinGecko
        import requests
        
        url = f"{COINGECKO_BASE_URL}/coins/{token_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": str(days),
            "interval": "daily" if days > 7 else None
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logger.error(f"CoinGecko API error: {response.status_code}")
            return pd.DataFrame()
        
        data = response.json()
        
        if not data or "prices" not in data:
            logger.error("No price data in historical response")
            return pd.DataFrame()
        
        # Convert to DataFrame
        price_data = data["prices"]
        df = pd.DataFrame(price_data, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        
        return df
    
    except Exception as e:
        logger.error(f"Error fetching historical data from CoinGecko: {str(e)}")
        return pd.DataFrame()

# Export key functions
__all__ = ['get_token_price', 'get_token_market_data', 'get_historical_data']
