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
    """Fetch detailed market data from CoinGecko API."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{COINGECKO_BASE_URL}/coins/{token_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false"
            }

            async with session.get(url, params=params) as response:
                if response.status == 404:
                    raise ValueError(ERROR_INVALID_TOKEN)

                data = await response.json()

                return {
                    "market_cap": data["market_data"]["market_cap"]["usd"],
                    "total_volume": data["market_data"]["total_volume"]["usd"],
                    "high_24h": data["market_data"]["high_24h"]["usd"],
                    "low_24h": data["market_data"]["low_24h"]["usd"],
                    "price_change_percentage_24h": data["market_data"]["price_change_percentage_24h"],
                    "market_cap_rank": data["market_cap_rank"]
                }
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to fetch market data: {str(e)}")