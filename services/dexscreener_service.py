import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

DEXSCREENER_BASE_URL = "https://api.dexscreener.com/latest"
SOLANA_CHAIN_ID = "solana"  # DEXScreener's chain ID for Solana

class TokenAlert:
    def __init__(self, token_address: str, target_price: float, is_above: bool):
        self.token_address = token_address
        self.target_price = target_price
        self.is_above = is_above
        self.triggered = False
        self.last_check = datetime.now()

# Store active token alerts
active_alerts: List[TokenAlert] = []

async def get_token_pairs(token_address: str) -> Optional[Dict[str, Any]]:
    """Fetch Solana token pairs data from DEXScreener."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DEXSCREENER_BASE_URL}/dex/tokens/{token_address}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                data = await response.json()

                # Filter for Solana pairs only
                if "pairs" in data:
                    solana_pairs = [pair for pair in data["pairs"] 
                                  if pair.get("chainId") == SOLANA_CHAIN_ID]
                    data["pairs"] = solana_pairs
                return data
        except Exception as e:
            print(f"DEXScreener API error: {str(e)}")
            return None

async def get_token_search(query: str) -> Optional[Dict[str, Any]]:
    """Search for Solana tokens on DEXScreener."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DEXSCREENER_BASE_URL}/dex/search"
            params = {"q": query}
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                data = await response.json()

                # Filter for Solana pairs only
                if "pairs" in data:
                    solana_pairs = [pair for pair in data["pairs"] 
                                  if pair.get("chainId") == SOLANA_CHAIN_ID]
                    data["pairs"] = solana_pairs
                return data
        except Exception as e:
            print(f"DEXScreener API error: {str(e)}")
            return None

async def get_trending_tokens() -> Optional[Dict[str, Any]]:
    """Get trending Solana tokens from DEXScreener."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{DEXSCREENER_BASE_URL}/dex/trending"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                data = await response.json()

                # Filter for Solana pairs only
                if "pairs" in data:
                    solana_pairs = [pair for pair in data["pairs"] 
                                  if pair.get("chainId") == SOLANA_CHAIN_ID]
                    data["pairs"] = solana_pairs
                return data
        except Exception as e:
            print(f"DEXScreener API error: {str(e)}")
            return None

async def add_price_alert(token_address: str, target_price: float, is_above: bool = True) -> bool:
    """Add a new price alert for a token."""
    # Verify token exists first
    token_data = await get_token_pairs(token_address)
    if not token_data or "pairs" not in token_data or not token_data["pairs"]:
        return False

    alert = TokenAlert(token_address, target_price, is_above)
    active_alerts.append(alert)
    return True

async def check_price_alerts() -> List[Dict[str, Any]]:
    """Check all active price alerts and return triggered ones."""
    triggered_alerts = []

    for alert in active_alerts:
        if alert.triggered:
            continue

        token_data = await get_token_pairs(alert.token_address)
        if not token_data or "pairs" not in token_data or not token_data["pairs"]:
            continue

        current_price = float(token_data["pairs"][0].get("priceUsd", 0))

        if ((alert.is_above and current_price >= alert.target_price) or
            (not alert.is_above and current_price <= alert.target_price)):
            alert.triggered = True
            triggered_alerts.append({
                "token_address": alert.token_address,
                "target_price": alert.target_price,
                "current_price": current_price,
                "token_name": token_data["pairs"][0].get("baseToken", {}).get("symbol", "Unknown"),
                "is_above": alert.is_above
            })

    return triggered_alerts

async def remove_price_alert(token_address: str, target_price: float) -> bool:
    """Remove a specific price alert."""
    for alert in active_alerts[:]:
        if alert.token_address == token_address and alert.target_price == target_price:
            active_alerts.remove(alert)
            return True
    return False