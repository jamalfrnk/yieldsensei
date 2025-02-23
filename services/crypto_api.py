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
                formatted_data = self._format_coingecko_data(data, symbol)
                logger.info(f"Formatted {symbol} price data: high_24h=${formatted_data['high_24h']:.2f}, low_24h=${formatted_data['low_24h']:.2f}")
                return formatted_data
        except Exception as e:
            logger.warning(f"CoinGecko API error: {str(e)}")

        try:
            # Fallback to DexScreener
            data = self._get_dexscreener_data(symbol)
            if data:
                logger.info(f"Successfully fetched {symbol} data from DexScreener")
                formatted_data = self._format_dexscreener_data(data)
                logger.info(f"Formatted {symbol} price data: high_24h=${formatted_data['high_24h']:.2f}, low_24h=${formatted_data['low_24h']:.2f}")
                return formatted_data
        except Exception as e:
            logger.error(f"DexScreener API error: {str(e)}")

        # Return default data if both APIs fail
        return self._get_default_data(symbol)

    def _get_coingecko_data(self, symbol: str) -> Optional[Dict]:
        """Fetch data from CoinGecko API"""
        coin_id = self._get_coingecko_id(symbol)
        if not coin_id:
            logger.warning(f"Could not find CoinGecko ID for symbol: {symbol}")
            return None

        logger.info(f"Fetching market chart data for {symbol} (coin_id: {coin_id})")
        response = self.session.get(
            f"{self.COINGECKO_BASE_URL}/coins/{coin_id}/market_chart",
            params={
                "vs_currency": "usd",
                "days": "30",
                "interval": "hourly"  # Changed to hourly for more accurate 24h high/low
            }
        )

        if response.status_code == 429:
            raise Exception("CoinGecko API rate limit reached")

        response.raise_for_status()
        historical_data = response.json()

        logger.info(f"Fetching current price data for {symbol}")
        current_data_response = self.session.get(
            f"{self.COINGECKO_BASE_URL}/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_vol": True,
                "include_24hr_change": True,
                "include_market_cap": True
            }
        )
        current_data = current_data_response.json()

        return {
            "historical": historical_data,
            "current": current_data.get(coin_id, {})
        }

    def _format_coingecko_data(self, data: Dict, symbol: str) -> Dict:
        """Format CoinGecko response to standard format with proper validation"""
        current_data = data.get("current", {})
        historical_prices = data.get("historical", {}).get("prices", [])

        # Calculate actual high/low from historical data
        if historical_prices:
            # Get timestamps and prices
            timestamps = [int(price[0]) for price in historical_prices]
            prices = [float(price[1]) for price in historical_prices]

            # Calculate time ranges
            now = int(datetime.now(timezone.utc).timestamp() * 1000)
            one_day_ago = now - (24 * 60 * 60 * 1000)

            # Get 24h price range
            prices_24h = [price for timestamp, price in zip(timestamps, prices) 
                         if timestamp >= one_day_ago]

            if prices_24h:
                high_24h = max(prices_24h)
                low_24h = min(prices_24h)
                logger.info(f"Calculated 24h range from {len(prices_24h)} data points: "
                          f"high=${high_24h:.2f}, low=${low_24h:.2f}")
            else:
                logger.warning("No 24h price data available, using current price")
                high_24h = low_24h = current_data.get("usd", 0)
        else:
            logger.warning("No historical price data available, using current price")
            high_24h = low_24h = current_data.get("usd", 0)

        # Sanity check for price ranges
        if high_24h < low_24h:
            logger.error("Invalid price range detected: high < low")
            high_24h, low_24h = max(high_24h, low_24h), min(high_24h, low_24h)

        # Additional validation for known assets
        coin_id = self._get_coingecko_id(symbol)
        current_price = current_data.get("usd", 0)

        if coin_id == "bitcoin":
            # Sanity check for Bitcoin (based on historical ranges)
            if high_24h > 100000 or low_24h < 10000:  # Unrealistic BTC prices as of 2025
                logger.error(f"Unrealistic Bitcoin price detected: ${high_24h:.2f}/${low_24h:.2f}")
                # Use current price with a reasonable range
                high_24h = current_price * 1.1  # Allow 10% variation
                low_24h = current_price * 0.9

        # Additional checks for other major assets can be added here
        elif coin_id == "ethereum":
            if high_24h > 10000 or low_24h < 100:  # Unrealistic ETH prices
                logger.error(f"Unrealistic Ethereum price detected: ${high_24h:.2f}/${low_24h:.2f}")
                high_24h = current_price * 1.1
                low_24h = current_price * 0.9

        formatted_data = {
            "current_price": current_price,
            "price_change_24h": current_data.get("usd_24h_change", 0),
            "market_cap": current_data.get("usd_market_cap", 0),
            "volume": current_data.get("usd_24h_vol", 0),
            "high_24h": high_24h,
            "low_24h": low_24h,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        return formatted_data

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

    def _format_dexscreener_data(self, data: Dict) -> Dict:
        """Format DexScreener response to standard format with proper validation"""
        pairs = data.get("pairs", [])
        if not pairs:
            return self._get_default_data("")

        # Use the first pair with highest volume
        pair = sorted(pairs, key=lambda x: float(x.get("volume", {}).get("h24", 0)), reverse=True)[0]

        current_price = float(pair.get("priceUsd", 0))
        price_change = float(pair.get("priceChange", {}).get("h24", 0))

        # Use actual price history for high/low instead of percentage-based calculation
        price_history = pair.get("priceHistory", {})
        if price_history:
            high_24h = max(float(p) for p in price_history.values())
            low_24h = min(float(p) for p in price_history.values())
        else:
            # Fallback to current price if no history available
            high_24h = current_price
            low_24h = current_price

        return {
            "current_price": current_price,
            "price_change_24h": price_change,
            "market_cap": float(pair.get("fdv", 0)),
            "volume": float(pair.get("volume", {}).get("h24", 0)),
            "high_24h": high_24h,
            "low_24h": low_24h,
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