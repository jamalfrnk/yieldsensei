import logging
import requests
from typing import Dict, Optional, Union
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class CryptoAPIService:
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
    DEXSCREENER_BASE_URL = "https://api.dexscreener.com/latest"
    
    def __init__(self):
        self.session = requests.Session()
        
    def get_market_data(self, symbol: str) -> Dict:
        """
        Get market data from CoinGecko with fallback to DexScreener
        """
        try:
            # Try CoinGecko first
            data = self._get_coingecko_data(symbol)
            if data:
                logger.info(f"Successfully fetched {symbol} data from CoinGecko")
                return self._format_coingecko_data(data)
        except Exception as e:
            logger.warning(f"CoinGecko API error: {str(e)}")
            
        try:
            # Fallback to DexScreener
            data = self._get_dexscreener_data(symbol)
            if data:
                logger.info(f"Successfully fetched {symbol} data from DexScreener")
                return self._format_dexscreener_data(data)
        except Exception as e:
            logger.error(f"DexScreener API error: {str(e)}")
            
        # Return default data if both APIs fail
        return self._get_default_data(symbol)
    
    def _get_coingecko_data(self, symbol: str) -> Optional[Dict]:
        """Fetch data from CoinGecko API"""
        coin_id = self._get_coingecko_id(symbol)
        if not coin_id:
            return None
            
        response = self.session.get(
            f"{self.COINGECKO_BASE_URL}/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false"
            }
        )
        
        if response.status_code == 429:
            raise Exception("CoinGecko API rate limit reached")
        
        response.raise_for_status()
        return response.json()
    
    def _get_dexscreener_data(self, symbol: str) -> Optional[Dict]:
        """Fetch data from DexScreener API"""
        response = self.session.get(
            f"{self.DEXSCREENER_BASE_URL}/dex/tokens/{symbol}"
        )
        response.raise_for_status()
        return response.json()
    
    def _get_coingecko_id(self, symbol: str) -> Optional[str]:
        """Convert symbol to CoinGecko ID"""
        symbol = symbol.lower()
        # Common mappings
        mappings = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "sol": "solana",
            "bnb": "binancecoin",
            "xrp": "ripple",
            "ada": "cardano",
            "doge": "dogecoin",
            "dot": "polkadot",
            "link": "chainlink"
        }
        return mappings.get(symbol, symbol)
    
    def _format_coingecko_data(self, data: Dict) -> Dict:
        """Format CoinGecko response to standard format"""
        market_data = data.get("market_data", {})
        return {
            "current_price": market_data.get("current_price", {}).get("usd", 0),
            "price_change_24h": market_data.get("price_change_percentage_24h", 0),
            "market_cap": market_data.get("market_cap", {}).get("usd", 0),
            "volume": market_data.get("total_volume", {}).get("usd", 0),
            "high_24h": market_data.get("high_24h", {}).get("usd", 0),
            "low_24h": market_data.get("low_24h", {}).get("usd", 0),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    def _format_dexscreener_data(self, data: Dict) -> Dict:
        """Format DexScreener response to standard format"""
        pairs = data.get("pairs", [])
        if not pairs:
            return self._get_default_data("")
            
        # Use the first pair with highest volume
        pair = sorted(pairs, key=lambda x: float(x.get("volume", {}).get("h24", 0)), reverse=True)[0]
        
        return {
            "current_price": float(pair.get("priceUsd", 0)),
            "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0)),
            "market_cap": float(pair.get("fdv", 0)),
            "volume": float(pair.get("volume", {}).get("h24", 0)),
            "high_24h": float(pair.get("priceUsd", 0)) * (1 + abs(float(pair.get("priceChange", {}).get("h24", 0)))/100),
            "low_24h": float(pair.get("priceUsd", 0)) * (1 - abs(float(pair.get("priceChange", {}).get("h24", 0)))/100),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_default_data(self, symbol: str) -> Dict:
        """Return default data structure when APIs fail"""
        logger.warning(f"Using default data for {symbol}")
        return {
            "current_price": 0.00,
            "price_change_24h": 0.00,
            "market_cap": 0,
            "volume": 0,
            "high_24h": 0.00,
            "low_24h": 0.00,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
