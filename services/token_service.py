import requests
import logging
from typing import Dict, Any, Optional
import os

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
        
        # Get detailed token data
        price_url = f"{COINGECKO_API_URL}/coins/{token_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "true"
        }
        
        response = requests.get(price_url, params=params)
        data = response.json()
        
        if not data or "market_data" not in data:
            logger.error(f"Invalid data received for token: {token_symbol}")
            return None
            
        market_data = data["market_data"]
        
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
                    "high": market_data["high_24h"]["usd"] * 1.1,  # Placeholder
                    "low": market_data["low_24h"]["usd"] * 0.9  # Placeholder
                },
                "month": {
                    "high": market_data["high_24h"]["usd"] * 1.2,  # Placeholder
                    "low": market_data["low_24h"]["usd"] * 0.8  # Placeholder
                },
                "quarter": {
                    "high": market_data["high_24h"]["usd"] * 1.3,  # Placeholder
                    "low": market_data["low_24h"]["usd"] * 0.7  # Placeholder
                },
                "year": {
                    "high": market_data["high_24h"]["usd"] * 1.5,  # Placeholder
                    "low": market_data["low_24h"]["usd"] * 0.5  # Placeholder
                }
            },
            "historical_data": [
                [str(point[0]), point[1]] 
                for point in data.get("sparkline_in_7d", {}).get("price", [])
            ] if data.get("sparkline_in_7d") else []
        }
        
    except Exception as e:
        logger.error(f"Error fetching token data: {str(e)}")
        return None
