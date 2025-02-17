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
            "days": "30",  # Increased to 30 days for better support/resistance calculation
            "interval": "hourly"
        }

        async with session.get(url, params=params) as response:
            data = await response.json()
            prices = [price[1] for price in data["prices"]]
            return np.array(prices)

def calculate_support_resistance(prices, n_levels=2):
    """Calculate support and resistance levels using price action."""
    try:
        # Convert to pandas Series for easier calculation
        price_series = pd.Series(prices)

        # Find local maxima and minima
        window = 20  # Window size for peak detection
        maxima = price_series[price_series.rolling(window, center=True).max() == price_series]
        minima = price_series[price_series.rolling(window, center=True).min() == price_series]

        # Get resistance levels (from maxima)
        resistance_levels = sorted(maxima.unique(), reverse=True)[:n_levels]

        # Get support levels (from minima)
        support_levels = sorted(minima.unique())[:n_levels]

        current_price = prices[-1]

        # Filter levels relative to current price
        resistance_levels = [level for level in resistance_levels if level > current_price]
        support_levels = [level for level in support_levels if level < current_price]

        # If no levels found above/below current price, use closest ones
        if not resistance_levels and len(sorted(maxima.unique())) > 0:
            resistance_levels = sorted(maxima.unique(), reverse=True)[:n_levels]
        if not support_levels and len(sorted(minima.unique())) > 0:
            support_levels = sorted(minima.unique())[:n_levels]

        return {
            "support_levels": support_levels[:n_levels],
            "resistance_levels": resistance_levels[:n_levels]
        }
    except Exception as e:
        print(f"Error calculating support/resistance: {str(e)}")
        # Return default values if calculation fails
        return {
            "support_levels": [prices[-1] * 0.95, prices[-1] * 0.90],
            "resistance_levels": [prices[-1] * 1.05, prices[-1] * 1.10]
        }

async def get_technical_analysis(token_id: str):
    """Calculate technical indicators and generate analysis using ta library."""
    try:
        prices = await get_historical_prices(token_id)
        if len(prices) < 30:
            raise ValueError("Insufficient price data for analysis")

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

        # Calculate support and resistance levels
        levels = calculate_support_resistance(prices)

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
            "rsi": float(current_rsi),  # Convert numpy types to native Python types
            "macd_signal": macd_signal,
            "bb_signal": bb_signal,
            "recommendation": recommendation,
            "current_price": float(current_price),
            "support_levels": [float(round(level, 2)) for level in levels["support_levels"]],
            "resistance_levels": [float(round(level, 2)) for level in levels["resistance_levels"]]
        }
    except Exception as e:
        print(f"Error in technical analysis for {token_id}: {str(e)}")
        raise Exception(f"Failed to perform technical analysis: {str(e)}")

async def generate_trading_signals(token_id: str):
    """Generate AI-driven trading signals based on technical indicators."""
    try:
        analysis = await get_technical_analysis(token_id)

        # Get price data for trend analysis
        prices = await get_historical_prices(token_id)
        price_changes = np.diff(prices) / prices[:-1] * 100

        # Calculate additional trend indicators
        trend_strength = np.abs(np.mean(price_changes[-5:]))  # 5-day trend strength
        volatility = np.std(price_changes[-14:])  # 14-day volatility

        # Generate comprehensive signal
        signal_strength = 0
        reasons = []

        # RSI signals
        if analysis['rsi'] < 30:
            signal_strength += 1
            reasons.append("Oversold (RSI)")
        elif analysis['rsi'] > 70:
            signal_strength -= 1
            reasons.append("Overbought (RSI)")

        # MACD signals
        if analysis['macd_signal'] == "Bullish":
            signal_strength += 1
            reasons.append("Bullish MACD crossover")
        elif analysis['macd_signal'] == "Bearish":
            signal_strength -= 1
            reasons.append("Bearish MACD crossover")

        # Bollinger Bands signals
        if analysis['bb_signal'] == "Oversold":
            signal_strength += 1
            reasons.append("Price below lower Bollinger Band")
        elif analysis['bb_signal'] == "Overbought":
            signal_strength -= 1
            reasons.append("Price above upper Bollinger Band")

        # Trend strength
        if trend_strength > 2:  # Significant trend
            if np.mean(price_changes[-5:]) > 0:
                signal_strength += 1
                reasons.append("Strong upward trend")
            else:
                signal_strength -= 1
                reasons.append("Strong downward trend")

        # Generate signal recommendation and DCA advice
        if signal_strength >= 2:
            signal = "Strong Buy"
            dca_advice = "Favorable conditions for DCA. Consider starting or increasing your regular investment amounts."
        elif signal_strength == 1:
            signal = "Buy"
            dca_advice = "Good opportunity for DCA. Maintain your regular investment schedule."
        elif signal_strength == 0:
            signal = "Neutral"
            dca_advice = "If already DCAing, maintain your regular schedule. For new positions, consider waiting for clearer signals."
        elif signal_strength == -1:
            signal = "Sell"
            dca_advice = "Consider pausing DCA and waiting for more favorable conditions."
        else:
            signal = "Strong Sell"
            dca_advice = "Not recommended for DCA. Wait for market conditions to improve."

        # Market conditions assessment
        market_conditions = "High volatility" if volatility > 5 else "Moderate volatility" if volatility > 2 else "Low volatility"
        if trend_strength > 3:
            market_conditions += " with strong trend"
        elif trend_strength > 1:
            market_conditions += " with moderate trend"
        else:
            market_conditions += " with weak trend"

        return {
            "signal": signal,
            "strength": abs(signal_strength),
            "reasons": reasons,
            "volatility": volatility,
            "trend_strength": trend_strength,
            "dca_advice": dca_advice,
            "market_conditions": market_conditions,
            "current_price": analysis["current_price"],
            "support_levels": analysis["support_levels"],
            "resistance_levels": analysis["resistance_levels"]
        }

    except Exception as e:
        raise Exception(f"Failed to generate trading signals: {str(e)}")