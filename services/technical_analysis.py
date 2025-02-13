import numpy as np
import pandas as pd
import aiohttp
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from config import COINGECKO_BASE_URL

async def get_historical_prices(token_id: str):
    """Fetch historical price data from CoinGecko."""
    async with aiohttp.ClientSession() as session:
        url = f"{COINGECKO_BASE_URL}/coins/{token_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "14",
            "interval": "daily"
        }

        async with session.get(url, params=params) as response:
            data = await response.json()
            prices = [price[1] for price in data["prices"]]
            return np.array(prices)

async def get_technical_analysis(token_id: str):
    """Calculate technical indicators and generate analysis using ta library."""
    try:
        prices = await get_historical_prices(token_id)
        df = pd.DataFrame(prices, columns=['close'])

        # Calculate RSI
        rsi = RSIIndicator(close=df['close'], window=14)
        current_rsi = rsi.rsi().iloc[-1]

        # Calculate MACD
        macd = MACD(close=df['close'])
        macd_line = macd.macd().iloc[-1]
        signal_line = macd.macd_signal().iloc[-1]

        # Calculate Bollinger Bands
        bb = BollingerBands(close=df['close'])
        upper = bb.bollinger_hband().iloc[-1]
        lower = bb.bollinger_lband().iloc[-1]
        current_price = prices[-1]

        # Generate signals
        macd_signal = "Bullish" if macd_line > signal_line else "Bearish"
        bb_signal = "Oversold" if current_price < lower else "Overbought" if current_price > upper else "Neutral"

        # Generate recommendation
        if current_rsi < 30 and current_price < lower:
            recommendation = "Strong Buy Signal"
        elif current_rsi > 70 and current_price > upper:
            recommendation = "Strong Sell Signal"
        else:
            recommendation = "Neutral"

        return {
            "rsi": current_rsi,
            "macd_signal": macd_signal,
            "bb_signal": bb_signal,
            "recommendation": recommendation
        }
    except Exception as e:
        raise Exception(f"Failed to perform technical analysis: {str(e)}")