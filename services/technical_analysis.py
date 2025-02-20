import logging
import numpy as np
import pandas as pd
import aiohttp
import os
from config import COINGECKO_BASE_URL
from services.ml_prediction_service import ml_service

# Configure logging
logger = logging.getLogger(__name__)

async def get_historical_prices(token_id: str):
    """Fetch historical price data from CoinGecko."""
    logger.info(f"Fetching historical prices for token: {token_id}")
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{COINGECKO_BASE_URL}/coins/{token_id}/market_chart"
            params = {
                "vs_currency": "usd",
                "days": "30",
                "interval": "daily"
            }
            logger.debug(f"Making API request to: {url}")

            async with session.get(url, params=params) as response:
                if response.status == 404:
                    logger.error(f"Token '{token_id}' not found in CoinGecko database")
                    raise ValueError(f"'{token_id}' not found in our database. Please check the token symbol or try using a contract address.")
                if response.status != 200:
                    logger.error(f"API error: {response.status}")
                    raise Exception("Unable to fetch market data at the moment. Please try again in a few minutes.")

                data = await response.json()
                if not data or "prices" not in data:
                    logger.error("Invalid response format from API")
                    raise Exception("Unable to process market data. Please try again later.")

                prices = [price[1] for price in data["prices"]]
                if not prices:
                    logger.error("No price data available")
                    raise Exception("No price data available for this token. Try a different token or check back later.")

                logger.info(f"Successfully fetched {len(prices)} price points for {token_id}")
                return np.array(prices)
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching prices: {str(e)}")
            raise Exception("Network connectivity issue. Please check your connection and try again.")
        except Exception as e:
            logger.error(f"Error fetching historical prices: {str(e)}")
            raise

def calculate_rsi(prices, periods=14):
    """Calculate RSI using pandas."""
    try:
        returns = pd.Series(prices).diff()
        gains = returns.where(returns > 0, 0)
        losses = -returns.where(returns < 0, 0)

        avg_gain = gains.rolling(window=periods).mean()
        avg_loss = losses.rolling(window=periods).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    except Exception as e:
        raise Exception(f"RSI calculation error: {str(e)}")

def calculate_macd(prices):
    """Calculate MACD using pandas."""
    try:
        price_series = pd.Series(prices)
        exp1 = price_series.ewm(span=12, adjust=False).mean()
        exp2 = price_series.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_value = float(macd.iloc[-1])
        signal_value = float(signal.iloc[-1])
        return macd_value > signal_value, abs(macd_value - signal_value)
    except Exception as e:
        raise Exception(f"MACD calculation error: {str(e)}")

def calculate_support_resistance(prices):
    """Calculate support and resistance levels using price clustering."""
    try:
        sorted_prices = np.sort(prices)
        price_range = sorted_prices[-1] - sorted_prices[0]
        current_price = prices[-1]

        clusters = []
        cluster_threshold = price_range * 0.015
        current_cluster = [sorted_prices[0]]

        for price in sorted_prices[1:]:
            if price - current_cluster[-1] <= cluster_threshold:
                current_cluster.append(price)
            else:
                if len(current_cluster) > 3:
                    clusters.append(np.mean(current_cluster))
                current_cluster = [price]

        if len(current_cluster) > 3:
            clusters.append(np.mean(current_cluster))

        clusters = np.array(clusters)
        supports = clusters[clusters < current_price]
        supports = np.sort(supports)[::-1]
        resistances = clusters[clusters > current_price]
        resistances = np.sort(resistances)

        if len(supports) < 2:
            support_levels = [
                current_price * 0.95,
                current_price * 0.90
            ] if len(supports) == 0 else [
                supports[0],
                supports[0] * 0.95
            ]
        else:
            support_levels = supports[:2]

        if len(resistances) < 2:
            resistance_levels = [
                current_price * 1.05,
                current_price * 1.10
            ] if len(resistances) == 0 else [
                resistances[0],
                resistances[0] * 1.05
            ]
        else:
            resistance_levels = resistances[:2]

        return {
            "support_1": support_levels[0],
            "support_2": support_levels[1],
            "resistance_1": resistance_levels[0],
            "resistance_2": resistance_levels[1]
        }
    except Exception as e:
        raise Exception(f"Support/Resistance calculation error: {str(e)}")

def calculate_optimal_levels(current_price, levels, signal_strength):
    """Calculate optimal entry and exit points based on price levels and signal strength."""
    try:
        support_1 = float(levels['support_1'])
        support_2 = float(levels['support_2'])
        resistance_1 = float(levels['resistance_1'])
        resistance_2 = float(levels['resistance_2'])

        # Calculate optimal entry based on signal strength and support levels
        if signal_strength > 60:  # Strong buy signal
            optimal_entry = current_price  # Enter immediately
            stop_loss = support_2  # Use second support as stop loss
        elif signal_strength > 20:  # Moderate buy signal
            optimal_entry = (current_price + support_1) / 2  # Enter halfway to support
            stop_loss = support_2
        elif signal_strength < -60:  # Strong sell signal
            optimal_entry = resistance_2  # Wait for strong resistance
            stop_loss = resistance_2 * 1.02  # Stop loss slightly above resistance
        elif signal_strength < -20:  # Moderate sell signal
            optimal_entry = resistance_1  # Wait for first resistance
            stop_loss = resistance_1 * 1.02
        else:  # Neutral
            optimal_entry = (current_price + support_1) / 2
            stop_loss = support_2

        # Calculate optimal exit based on resistance levels
        if signal_strength > 0:
            optimal_exit = resistance_1  # Target first resistance for profit
        else:
            optimal_exit = support_1  # Exit at first support if bearish

        return {
            'optimal_entry': optimal_entry,
            'optimal_exit': optimal_exit,
            'stop_loss': stop_loss
        }
    except Exception as e:
        logger.error(f"Error calculating optimal levels: {str(e)}")
        # Provide default values based on current price if calculation fails
        return {
            'optimal_entry': current_price * 0.98,
            'optimal_exit': current_price * 1.05,
            'stop_loss': current_price * 0.95
        }

async def get_signal_analysis(token_id: str):
    """Generate detailed trading signal analysis with ML-enhanced predictions."""
    logger.info(f"Starting signal analysis for token: {token_id}")
    try:
        prices = await get_historical_prices(token_id)
        current_price = prices[-1]
        logger.info(f"Current price: ${current_price:,.2f}")

        # Calculate indicators and levels
        current_rsi = calculate_rsi(prices)
        is_macd_bullish, macd_strength = calculate_macd(prices)
        levels = calculate_support_resistance(prices)

        # Get ML predictions if models are available
        try:
            ml_predictions = await ml_service.predict_price(prices)
        except Exception as e:
            logger.warning(f"ML prediction failed: {str(e)}")
            ml_predictions = None

        # Calculate signal strength
        signal_strength = calculate_enhanced_signal_strength(
            current_price=current_price,
            current_rsi=current_rsi,
            is_macd_bullish=is_macd_bullish,
            macd_strength=macd_strength,
            levels=levels,
            ml_predictions=ml_predictions
        )

        # Calculate optimal trading levels
        optimal_levels = calculate_optimal_levels(current_price, levels, signal_strength)

        # Determine signal type and build response
        signal = get_signal_type(signal_strength)

        result = {
            'signal': signal,
            'signal_strength': abs(signal_strength),
            'trend_direction': "Bullish 📈" if signal_strength > 0 else "Bearish 📉" if signal_strength < 0 else "Neutral ⚖️",
            'current_price': f"${current_price:,.2f}",
            'rsi': current_rsi,
            'macd_signal': "Bullish 📈" if is_macd_bullish else "Bearish 📉",
            'support_1': f"${levels['support_1']:,.2f}",
            'support_2': f"${levels['support_2']:,.2f}",
            'resistance_1': f"${levels['resistance_1']:,.2f}",
            'resistance_2': f"${levels['resistance_2']:,.2f}",
            'optimal_entry': optimal_levels['optimal_entry'],
            'optimal_exit': optimal_levels['optimal_exit'],
            'stop_loss': optimal_levels['stop_loss'],
            'ml_predictions': ml_predictions if ml_predictions else {},
            'dca_recommendation': get_enhanced_dca_recommendation(signal_strength, ml_predictions)
        }

        logger.info("Successfully generated signal analysis")
        return result

    except Exception as e:
        logger.error(f"Failed to generate signal analysis: {str(e)}")
        raise Exception(f"Failed to generate signal analysis: {str(e)}")

def calculate_enhanced_signal_strength(current_price, current_rsi, is_macd_bullish, macd_strength, levels, ml_predictions):
    """Calculate signal strength incorporating ML predictions."""
    signal_strength = 0

    # Traditional indicators contribution (60% weight)
    # RSI contribution (25%)
    if current_rsi < 30:
        signal_strength += 25 * (1 - current_rsi/30)
    elif current_rsi > 70:
        signal_strength -= 25 * (current_rsi-70)/30

    # MACD contribution (20%)
    if is_macd_bullish:
        signal_strength += 20 * (macd_strength/abs(current_price))
    else:
        signal_strength -= 20 * (macd_strength/abs(current_price))

    # Support/Resistance contribution (15%)
    price_to_support1 = (current_price - levels['support_1']) / current_price
    price_to_resistance1 = (levels['resistance_1'] - current_price) / current_price

    if price_to_support1 < 0.03:
        signal_strength += 15 * (1 - price_to_support1/0.03)
    elif price_to_resistance1 < 0.03:
        signal_strength -= 15 * (1 - price_to_resistance1/0.03)

    # ML predictions contribution (40% weight)
    if ml_predictions and 'next_day' in ml_predictions:
        pred_price = ml_predictions['next_day']['prophet_prediction']
        price_change = (pred_price - current_price) / current_price
        confidence = ml_predictions['confidence_score'] / 100

        # Add ML signal (-40 to +40 range)
        ml_signal = 40 * price_change * confidence
        signal_strength += ml_signal

    return signal_strength

def get_enhanced_dca_recommendation(signal_strength, ml_predictions):
    """Get enhanced DCA recommendation incorporating ML predictions."""
    base_recommendation = get_dca_recommendation(signal_strength)

    if not ml_predictions or 'next_day' not in ml_predictions:
        return base_recommendation

    confidence_score = ml_predictions['confidence_score']
    pred_change = (ml_predictions['next_day']['prophet_prediction'] - 
                  float(ml_predictions['next_day']['rf_prediction'])) / \
                 float(ml_predictions['next_day']['rf_prediction'])

    # Add ML-specific insights
    ml_insights = (
        f"\n\n💡 ML Analysis:\n"
        f"• Prediction Confidence: {confidence_score:.1f}%\n"
        f"• Expected Price Range: ${ml_predictions['next_day']['lower_bound']:,.2f} "
        f"to ${ml_predictions['next_day']['upper_bound']:,.2f}\n"
    )

    if confidence_score > 70:
        ml_insights += "• High confidence in predictions - consider following signals more aggressively\n"
    elif confidence_score < 30:
        ml_insights += "• Low confidence in predictions - maintain conservative position sizing\n"

    return base_recommendation + ml_insights

def get_signal_type(signal_strength):
    """Determine signal type based on signal strength."""
    if signal_strength > 60:
        return "Strong Buy 🟢"
    elif signal_strength > 20:
        return "Moderate Buy 🟡"
    elif signal_strength < -60:
        return "Strong Sell 🔴"
    elif signal_strength < -20:
        return "Moderate Sell 🟡"
    else:
        return "Neutral ⚖️"

def get_dca_recommendation(signal_strength):
    """Get DCA recommendation based on signal strength."""
    if signal_strength > 60:
        return (
            "💡 DCA Strategy:\n"
            "• Consider splitting your investment into 3-4 portions\n"
            "• Invest 40% now while momentum is strong\n"
            "• Space out remaining portions over 1-2 weeks\n"
            "• Set stop-loss just below Support 2"
        )
    elif signal_strength > 20:
        return (
            "💡 DCA Strategy:\n"
            "• Split investment into 5-6 smaller portions\n"
            "• Invest 25% now at current levels\n"
            "• Space out remaining portions over 2-3 weeks\n"
            "• Set stop-loss between Support 1 and 2"
        )
    elif signal_strength < -60:
        return (
            "💡 DCA Exit Strategy:\n"
            "• Consider selling 40-50% of position now\n"
            "• Set limit orders near Resistance 1 for remaining exit\n"
            "• Space out sells over 3-4 days\n"
            "• Keep small position (10-15%) for potential breakout"
        )
    elif signal_strength < -20:
        return (
            "💡 DCA Exit Strategy:\n"
            "• Consider selling 25-30% of position now\n"
            "• Set limit orders near Resistance 1 for remaining exit\n"
            "• Space out sells over 1-2 weeks\n"
            "• Keep 20-25% position for potential breakout"
        )
    else:
        return (
            "💡 Neutral Strategy:\n"
            "• Market shows mixed signals\n"
            "• Consider waiting for clearer direction\n"
            "• Set alerts at Support 1 and Resistance 1\n"
            "• Focus on portfolio rebalancing"
        )