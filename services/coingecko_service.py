import aiohttp
from config import COINGECKO_BASE_URL, ERROR_INVALID_TOKEN

async def get_token_price(token_id: str):
    """Fetch token price data from CoinGecko API."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{COINGECKO_BASE_URL}/simple/price"
            params = {
                "ids": token_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }

            async with session.get(url, params=params) as response:
                if response.status == 404:
                    raise ValueError(ERROR_INVALID_TOKEN)

                data = await response.json()

                if token_id not in data:
                    raise ValueError(ERROR_INVALID_TOKEN)

                return {
                    "usd": data[token_id]["usd"],
                    "usd_24h_change": data[token_id]["usd_24h_change"]
                }
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to fetch price data: {str(e)}")

async def get_token_market_data(token_id: str):
    """Fetch detailed market data including historical prices from CoinGecko API."""
    async with aiohttp.ClientSession() as session:
        try:
            # Get current market data
            url = f"{COINGECKO_BASE_URL}/coins/{token_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false"
            }

            async with session.get(url, params=params) as response:
                if response.status == 404:
                    raise ValueError(ERROR_INVALID_TOKEN)

                data = await response.json()
                market_data = data["market_data"]

            # Get historical price data (last 365 days)
            history_url = f"{COINGECKO_BASE_URL}/coins/{token_id}/market_chart"
            history_params = {
                "vs_currency": "usd",
                "days": "365",
                "interval": "daily"
            }

            async with session.get(history_url, params=history_params) as history_response:
                if history_response.status == 404:
                    raise ValueError(ERROR_INVALID_TOKEN)

                history_data = await history_response.json()

                if not history_data or "prices" not in history_data:
                    raise ValueError("No historical price data available")

                return {
                    "market_cap": market_data["market_cap"]["usd"],
                    "total_volume": market_data["total_volume"]["usd"],
                    "high_24h": market_data["high_24h"]["usd"],
                    "low_24h": market_data["low_24h"]["usd"],
                    "price_change_percentage_24h": market_data["price_change_percentage_24h"],
                    "market_cap_rank": data["market_cap_rank"],
                    "prices": history_data["prices"]  # Array of [timestamp, price] pairs
                }

        except aiohttp.ClientError as e:
            raise Exception(f"Failed to fetch market data: {str(e)}")
        except KeyError as e:
            raise Exception(f"Invalid market data format: {str(e)}")