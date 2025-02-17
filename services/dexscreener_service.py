
import aiohttp
from typing import Dict, Any, Optional

DEXSCREENER_BASE_URL = "https://api.dexscreener.com/latest"

async def get_token_pairs(token_address: str) -> Optional[Dict[str, Any]]:
    """Fetch token pairs data from DEXScreener."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DEXSCREENER_BASE_URL}/dex/tokens/{token_address}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                return await response.json()
        except Exception as e:
            print(f"DEXScreener API error: {str(e)}")
            return None

async def get_token_search(query: str) -> Optional[Dict[str, Any]]:
    """Search for tokens on DEXScreener."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DEXSCREENER_BASE_URL}/dex/search"
            params = {"q": query}
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                return await response.json()
        except Exception as e:
            print(f"DEXScreener API error: {str(e)}")
            return None
