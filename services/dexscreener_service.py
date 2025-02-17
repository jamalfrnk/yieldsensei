import aiohttp
from typing import Dict, Any, Optional

DEXSCREENER_BASE_URL = "https://api.dexscreener.com/latest"
SOLANA_CHAIN_ID = "solana"  # DEXScreener's chain ID for Solana

async def get_token_pairs(token_address: str) -> Optional[Dict[str, Any]]:
    """Fetch Solana token pairs data from DEXScreener."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DEXSCREENER_BASE_URL}/dex/tokens/{token_address}"
            async with session.get(url) as response:
                if response.status != 200:
                    return {"pairs": [], "error": "Failed to fetch token data"}

                data = await response.json()
                if not data or "pairs" not in data:
                    return {"pairs": [], "error": "Invalid response format"}

                # Filter for Solana pairs only
                solana_pairs = [pair for pair in data.get("pairs", []) 
                              if pair.get("chainId") == SOLANA_CHAIN_ID]

                # Format price changes
                for pair in solana_pairs:
                    if "priceChange" in pair and "h24" in pair["priceChange"]:
                        try:
                            change = float(pair["priceChange"]["h24"])
                            pair["priceChange"]["h24"] = f"{change:+.2f}"  # Add plus sign for positive changes
                        except (ValueError, TypeError):
                            pair["priceChange"]["h24"] = "N/A"

                return {"pairs": solana_pairs}

        except aiohttp.ClientError as e:
            print(f"DEXScreener API error: {str(e)}")
            return {"pairs": [], "error": f"API error: {str(e)}"}
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return {"pairs": [], "error": "Unexpected error occurred"}