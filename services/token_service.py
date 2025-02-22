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

        # Get detailed token data with market data and sparkline - now 90 days
        price_url = f"{COINGECKO_API_URL}/coins/{token_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "90",  # Changed from 30 to 90 days
            "interval": "daily"
        }

        response = requests.get(price_url, params=params)
        chart_data = response.json()

        # Get current price and other market data
        price_url = f"{COINGECKO_API_URL}/coins/{token_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false"
        }

        response = requests.get(price_url, params=params)
        data = response.json()

        if not data or "market_data" not in data:
            logger.error(f"Invalid data received for token: {token_symbol}")
            return None

        market_data = data["market_data"]

        # Format historical data for Chart.js - full 90 days
        historical_data = []
        if "prices" in chart_data:
            historical_data = [
                [
                    datetime.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d"),
                    price
                ]
                for timestamp, price in chart_data["prices"]
            ]

        return {
            "token_symbol": data["symbol"].upper(),
            "price": market_data["current_price"]["usd"],
            "price_change": market_data["price_change_percentage_24h"],
            "market_cap": market_data["market_cap"]["usd"],
            "volume": market_data["total_volume"]["usd"],
            "high_24h": market_data["high_24h"]["usd"],
            "low_24h": market_data["low_24h"]["usd"],
            "price_ranges": {
                "day": {
                    "high": market_data["high_24h"]["usd"],
                    "low": market_data["low_24h"]["usd"]
                },
                "week": {
                    "high": max(price for _, price in historical_data[-7:]) if historical_data else market_data["high_24h"]["usd"],
                    "low": min(price for _, price in historical_data[-7:]) if historical_data else market_data["low_24h"]["usd"]
                },
                "month": {
                    "high": max(price for _, price in historical_data[-30:]) if historical_data else market_data["high_24h"]["usd"],
                    "low": min(price for _, price in historical_data[-30:]) if historical_data else market_data["low_24h"]["usd"]
                },
                "quarter": {
                    "high": max(price for _, price in historical_data) if historical_data else market_data["ath"]["usd"],
                    "low": min(price for _, price in historical_data) if historical_data else market_data["atl"]["usd"]
                },
                "year": {
                    "high": market_data["ath"]["usd"],
                    "low": market_data["atl"]["usd"]
                }
            },
            "historical_data": historical_data
        }

    except Exception as e:
        logger.error(f"Error fetching token data: {str(e)}")
        return None