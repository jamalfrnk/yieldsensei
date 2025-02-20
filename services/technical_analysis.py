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

async def get_signal_analysis(token_id: str):
    """Generate detailed trading signal analysis with ML-enhanced predictions."""
    logger.info(f"Starting signal analysis for token: {token_id}")
    try:
        logger.info("Fetching historical price data")
        prices = await get_historical_prices(token_id)
        current_price = prices[-1]
        logger.info(f"Current price: ${current_price:,.2f}")

        # Train ML models if needed
        if not os.path.exists('models/rf_model.joblib'):
            logger.info("Training ML models with historical data")
            ml_service.train_models(prices)

        # Get ML predictions
        logger.info("Generating ML predictions")
        ml_predictions = await ml_service.predict_price(prices)

        # Calculate traditional indicators
        logger.info("Calculating technical indicators")
        current_rsi = calculate_rsi(prices)
        logger.info(f"RSI: {current_rsi:.2f}")

        is_macd_bullish, macd_strength = calculate_macd(prices)
        macd_signal = "Bullish 📈" if is_macd_bullish else "Bearish 📉"
        logger.info(f"MACD Signal: {macd_signal}")

        logger.info("Calculating support and resistance levels")
        levels = calculate_support_resistance(prices)

        # Calculate enhanced signal strength incorporating ML predictions
        logger.info("Calculating overall signal strength")
        signal_strength = calculate_enhanced_signal_strength(
            current_price=current_price,
            current_rsi=current_rsi,
            is_macd_bullish=is_macd_bullish,
            macd_strength=macd_strength,
            levels=levels,
            ml_predictions=ml_predictions
        )


        # Determine signal type
        signal = get_signal_type(signal_strength)
        logger.info(f"Generated signal: {signal}")

        # Build and return the analysis result
        result = {
            "signal": signal,
            "signal_strength": abs(signal_strength),
            "trend_direction": "Bullish 📈" if signal_strength > 0 else "Bearish 📉" if signal_strength < 0 else "Neutral ⚖️",
            "current_price": f"${current_price:,.2f}",
            "rsi": current_rsi,
            "macd_signal": macd_signal,
            "support_1": f"${levels['support_1']:,.2f}",
            "support_2": f"${levels['support_2']:,.2f}",
            "resistance_1": f"${levels['resistance_1']:,.2f}",
            "resistance_2": f"${levels['resistance_2']:,.2f}",
            "ml_predictions": ml_predictions if ml_predictions else {},
            "dca_recommendation": get_enhanced_dca_recommendation(signal_strength, ml_predictions)
        }

        logger.info("Successfully generated signal analysis with ML predictions")
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