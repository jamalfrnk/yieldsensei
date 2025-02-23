
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from logging import getLogger

logger = getLogger(__name__)
DEXSCREENER_BASE_URL = "https://api.dexscreener.com/latest"
SOLANA_CHAIN_ID = "solana"

async def get_token_pairs(token_address: str) -> Optional[Dict[str, Any]]:
    """Fetch Solana token pairs data from DEXScreener."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DEXSCREENER_BASE_URL}/dex/tokens/{token_address}"
            async with session.get(url, timeout=10) as response:
                if response.status == 429:  # Rate limit
                    await asyncio.sleep(2)  # Wait before retry
                    return await get_token_pairs(token_address)
                    
                if response.status != 200:
                    logger.error(f"DEXScreener API error: {response.status}")
                    return {"pairs": [], "error": f"API error: Status {response.status}"}

                data = await response.json()
                if not data or "pairs" not in data:
                    logger.warning("Invalid response format from DEXScreener")
                    return {"pairs": [], "error": "Invalid response format"}

                solana_pairs = [pair for pair in data.get("pairs", []) 
                              if pair.get("chainId") == SOLANA_CHAIN_ID]

                if not solana_pairs:
                    logger.info(f"No Solana pairs found for {token_address}")

                for pair in solana_pairs:
                    if "priceChange" in pair and "h24" in pair["priceChange"]:
                        try:
                            change = float(pair["priceChange"]["h24"])
                            pair["priceChange"]["h24"] = f"{change:+.2f}"
                        except (ValueError, TypeError):
                            pair["priceChange"]["h24"] = "N/A"

                return {"pairs": solana_pairs}

        except asyncio.TimeoutError:
            logger.error("DEXScreener API timeout")
            return {"pairs": [], "error": "Request timeout"}
        except aiohttp.ClientError as e:
            logger.error(f"DEXScreener API error: {str(e)}")
            return {"pairs": [], "error": f"API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"pairs": [], "error": "Unexpected error occurred"}
