import numpy as np
import pandas as pd
import aiohttp
from config import COINGECKO_BASE_URL

async def get_historical_prices(token_id: str):
    """Fetch historical price data from CoinGecko."""
    async with aiohttp.ClientSession() as session:
        url = f"{COINGECKO_BASE_URL}/coins/{token_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "30",  # Extended to 30 days for better support/resistance
            "interval": "daily"
        }

        async with session.get(url, params=params) as response:
            data = await response.json()
            prices = [price[1] for price in data["prices"]]
            return np.array(prices)

def calculate_rsi(prices, periods=14):
    """Calculate RSI using pandas."""
    returns = pd.Series(prices).diff()
    gains = returns.where(returns > 0, 0)
    losses = -returns.where(returns < 0, 0)

    avg_gain = gains.rolling(window=periods).mean()
    avg_loss = losses.rolling(window=periods).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_macd(prices):
    """Calculate MACD using pandas."""
    price_series = pd.Series(prices)
    exp1 = price_series.ewm(span=12, adjust=False).mean()
    exp2 = price_series.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    macd_value = macd.iloc[-1]
    signal_value = signal.iloc[-1]
    return macd_value > signal_value, abs(macd_value - signal_value)

def calculate_support_resistance(prices):
    """Calculate two levels of support and resistance using improved price clustering."""
    # Sort prices and remove duplicates
    sorted_prices = np.sort(prices)
    price_range = sorted_prices[-1] - sorted_prices[0]

    # Define price clusters with adaptive threshold
    clusters = []
    cluster_threshold = price_range * 0.015  # Reduced to 1.5% for more precise levels
    current_cluster = [sorted_prices[0]]

    for price in sorted_prices[1:]:
        if price - current_cluster[-1] <= cluster_threshold:
            current_cluster.append(price)
        else:
            if len(current_cluster) > 3:  # Increased minimum points for stronger levels
                clusters.append(np.mean(current_cluster))
            current_cluster = [price]

    if len(current_cluster) > 3:
        clusters.append(np.mean(current_cluster))

    clusters = np.array(clusters)
    current_price = prices[-1]

    # Find support levels (below current price)
    supports = clusters[clusters < current_price]
    supports = np.sort(supports)[::-1]  # Sort descending

    # Ensure proper spacing between support levels
    min_level_spacing = price_range * 0.01  # 1% minimum spacing
    filtered_supports = []
    for s in supports:
        if not filtered_supports or abs(s - filtered_supports[-1]) >= min_level_spacing:
            filtered_supports.append(s)
        if len(filtered_supports) == 2:
            break

    support_levels = filtered_supports if len(filtered_supports) >= 2 else \
                    np.append(filtered_supports, [filtered_supports[-1] * 0.95] * (2 - len(filtered_supports)))

    # Find resistance levels (above current price)
    resistances = clusters[clusters > current_price]
    resistances = np.sort(resistances)  # Sort ascending

    # Ensure proper spacing between resistance levels
    filtered_resistances = []
    for r in resistances:
        if not filtered_resistances or abs(r - filtered_resistances[-1]) >= min_level_spacing:
            filtered_resistances.append(r)
        if len(filtered_resistances) == 2:
            break

    resistance_levels = filtered_resistances if len(filtered_resistances) >= 2 else \
                       np.append(filtered_resistances, [filtered_resistances[-1] * 1.05] * (2 - len(filtered_resistances)))

    return {
        "support_1": support_levels[0],
        "support_2": support_levels[1],
        "resistance_1": resistance_levels[0],
        "resistance_2": resistance_levels[1]
    }

async def get_signal_analysis(token_id: str):
    """Generate detailed buy/sell signals with DCA recommendations."""
    try:
        prices = await get_historical_prices(token_id)
        current_price = prices[-1]

        # Calculate RSI
        current_rsi = calculate_rsi(prices)

        # Calculate MACD
        is_macd_bullish, macd_strength = calculate_macd(prices)
        macd_signal = "Bullish" if is_macd_bullish else "Bearish"

        # Calculate support and resistance levels
        levels = calculate_support_resistance(prices)

        # Generate signal strength (0 to 100)
        signal_strength = 0

        # RSI contribution (max 40 points)
        if current_rsi < 30:
            signal_strength += 40 * (1 - current_rsi/30)  # Strong buy
        elif current_rsi > 70:
            signal_strength -= 40 * (current_rsi-70)/30  # Strong sell

        # MACD contribution (max 30 points)
        if is_macd_bullish:
            signal_strength += 30 * (macd_strength/abs(current_price))  # Bullish
        else:
            signal_strength -= 30 * (macd_strength/abs(current_price))  # Bearish

        # Support/Resistance contribution (max 30 points)
        price_to_support1 = (current_price - levels['support_1']) / current_price
        price_to_resistance1 = (levels['resistance_1'] - current_price) / current_price

        if price_to_support1 < 0.03:  # Near support
            signal_strength += 30 * (1 - price_to_support1/0.03)
        elif price_to_resistance1 < 0.03:  # Near resistance
            signal_strength -= 30 * (1 - price_to_resistance1/0.03)

        # Determine signal type and DCA recommendations
        if signal_strength > 60:
            signal = "Strong Buy 🟢"
            dca_recommendation = (
                "💡 DCA Strategy:\n"
                "• Consider splitting your investment into 3-4 portions\n"
                "• Invest 40% now while momentum is strong\n"
                "• Space out remaining portions over 1-2 weeks\n"
                "• Set stop-loss just below Support 2"
            )
        elif signal_strength > 20:
            signal = "Moderate Buy 🟡"
            dca_recommendation = (
                "💡 DCA Strategy:\n"
                "• Split investment into 5-6 smaller portions\n"
                "• Invest 25% now at current levels\n"
                "• Space out remaining portions over 2-3 weeks\n"
                "• Set stop-loss between Support 1 and 2"
            )
        elif signal_strength < -60:
            signal = "Strong Sell 🔴"
            dca_recommendation = (
                "💡 DCA Exit Strategy:\n"
                "• Consider selling 40-50% of position now\n"
                "• Set limit orders near Resistance 1 for remaining exit\n"
                "• Space out sells over 3-4 days\n"
                "• Keep small position (10-15%) for potential breakout above Resistance 2"
            )
        elif signal_strength < -20:
            signal = "Moderate Sell 🟡"
            dca_recommendation = (
                "💡 DCA Exit Strategy:\n"
                "• Consider selling 25-30% of position now\n"
                "• Set limit orders near Resistance 1 for remaining exit\n"
                "• Space out sells over 1-2 weeks\n"
                "• Keep 20-25% position for potential breakout"
            )
        else:
            signal = "Neutral ⚖️"
            dca_recommendation = (
                "💡 Neutral Strategy:\n"
                "• Market shows mixed signals\n"
                "• Consider waiting for clearer direction\n"
                "• Set alerts at Support 1 and Resistance 1\n"
                "• Focus on portfolio rebalancing"
            )

        return {
            "signal": signal,
            "signal_strength": abs(signal_strength),
            "trend_direction": "Bullish" if signal_strength > 0 else "Bearish" if signal_strength < 0 else "Neutral",
            "rsi": current_rsi,
            "macd_signal": macd_signal,
            "support_1": f"${levels['support_1']:,.2f}",
            "support_2": f"${levels['support_2']:,.2f}",
            "resistance_1": f"${levels['resistance_1']:,.2f}",
            "resistance_2": f"${levels['resistance_2']:,.2f}",
            "dca_recommendation": dca_recommendation
        }
    except Exception as e:
        raise Exception(f"Failed to generate signal analysis: {str(e)}")