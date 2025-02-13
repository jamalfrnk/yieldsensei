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
