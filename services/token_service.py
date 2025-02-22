import requests
import logging
from typing import Dict, Any, Optional
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

def get_token_data(token_symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch comprehensive token data including price and market info."""
    try:
        # Get token id from symbol
        search_url = f"{COINGECKO_API_URL}/search"
        search_response = requests.get(search_url, params={"query": token_symbol})
        search_data = search_response.json()

        if not search_data.get("coins"):
            logger.warning(f"No token found for symbol: {token_symbol}")
            return None

        token_id = search_data["coins"][0]["id"]
        logger.info(f"Found token ID: {token_id} for symbol: {token_symbol}")

        # Get OHLC data
        ohlc_url = f"{COINGECKO_API_URL}/coins/{token_id}/ohlc"
        params = {
            "vs_currency": "usd",
            "days": "90"
        }

        ohlc_response = requests.get(ohlc_url, params=params)
        if ohlc_response.status_code != 200:
            logger.error(f"Failed to fetch OHLC data: {ohlc_response.text}")
            return None

        ohlc_data = ohlc_response.json()
        if not isinstance(ohlc_data, list):
            logger.error(f"Invalid OHLC data format: {ohlc_data}")
            return None

        # Get market data
        market_url = f"{COINGECKO_API_URL}/coins/{token_id}"
        market_params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false"
        }

        market_response = requests.get(market_url, params=market_params)
        if market_response.status_code != 200:
            logger.error(f"Failed to fetch market data: {market_response.text}")
            return None

        market_data = market_response.json()
        if not market_data.get("market_data"):
            logger.error("Market data not found in response")
            return None

        # Format OHLC data for Chart.js
        historical_data = [
            {
                'time': datetime.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d"),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close
            }
            for timestamp, open_price, high, low, close in ohlc_data
        ]

        # Calculate ranges from OHLC data
        def get_range_from_ohlc(data_slice):
            if not data_slice:
                return {
                    'high': market_data['market_data']['high_24h']['usd'],
                    'low': market_data['market_data']['low_24h']['usd']
                }
            return {
                'high': max(point['high'] for point in data_slice),
                'low': min(point['low'] for point in data_slice)
            }

        market_data_section = market_data["market_data"]

        return {
            "token_symbol": market_data["symbol"].upper(),
            "price": market_data_section["current_price"]["usd"],
            "price_change": market_data_section["price_change_percentage_24h"],
            "market_cap": market_data_section["market_cap"]["usd"],
            "volume": market_data_section["total_volume"]["usd"],
            "high_24h": market_data_section["high_24h"]["usd"],
            "low_24h": market_data_section["low_24h"]["usd"],
            "price_ranges": {
                "day": {
                    "high": market_data_section["high_24h"]["usd"],
                    "low": market_data_section["low_24h"]["usd"]
                },
                "week": get_range_from_ohlc(historical_data[-7:]),
                "month": get_range_from_ohlc(historical_data[-30:]),
                "quarter": get_range_from_ohlc(historical_data),
                "year": {
                    "high": market_data_section["ath"]["usd"],
                    "low": market_data_section["atl"]["usd"]
                }
            },
            "historical_data": historical_data
        }

    except Exception as e:
        logger.error(f"Error fetching token data: {str(e)}", exc_info=True)
        return None