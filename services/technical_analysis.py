import logging
import numpy as np
import pandas as pd
import aiohttp
import os
import asyncio
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
                "days": "90",
                "interval": "daily"
            }
            logger.debug(f"Making API request to: {url}")

            async with session.get(url, params=params) as response:
                if response.status == 404:
                    logger.error(f"Token '{token_id}' not found in CoinGecko database")
                    raise ValueError(f"'{token_id}' not found in our database. Please check the token symbol.")
                if response.status != 200:
                    logger.error(f"API error: {response.status}")
                    raise Exception("Unable to fetch market data. Please try again later.")

                data = await response.json()
                if not data or "prices" not in data:
                    logger.error("Invalid response format from API")
                    raise Exception("Unable to process market data. Please try again later.")

                prices = [price[1] for price in data["prices"]]
                if not prices:
                    logger.error("No price data available")
                    raise Exception("No price data available for this token.")

                logger.info(f"Successfully fetched {len(prices)} price points for {token_id}")
                return np.array(prices)
        except Exception as e:
            logger.error(f"Error fetching historical prices: {str(e)}")
            raise

def calculate_rsi(prices, periods=14, ema_alpha=None):
    """Calculate RSI using exponential smoothing with improved accuracy."""
    try:
        if len(prices) < periods + 1:
            logger.warning("Insufficient data for RSI calculation")
            return 50.0

        price_series = pd.Series(prices)
        returns = price_series.diff()

        # Use exponential smoothing if alpha is provided
        if ema_alpha:
            gains = returns.where(returns > 0, 0).ewm(alpha=ema_alpha, adjust=False).mean()
            losses = -returns.where(returns < 0, 0).ewm(alpha=ema_alpha, adjust=False).mean()
        else:
            # Standard RSI calculation
            gains = returns.where(returns > 0, 0).rolling(window=periods, min_periods=1).mean()
            losses = -returns.where(returns < 0, 0).rolling(window=periods, min_periods=1).mean()

        # Handle zero division cases
        rs = gains / losses.replace(0, float('inf'))
        rsi = 100 - (100 / (1 + rs))

        # Clean up the results
        rsi = rsi.fillna(50)  # Fill NaN values with neutral RSI
        rsi = rsi.clip(0, 100)  # Ensure RSI is between 0 and 100

        # Calculate RSI trend
        rsi_trend = "Overbought" if rsi.iloc[-1] > 70 else "Oversold" if rsi.iloc[-1] < 30 else "Neutral"
        rsi_strength = abs(50 - rsi.iloc[-1]) / 50  # 0 to 1 scale

        latest_rsi = float(rsi.iloc[-1])
        logger.info(f"Calculated RSI: {latest_rsi}, Trend: {rsi_trend}")
        return latest_rsi, rsi_trend, rsi_strength

    except Exception as e:
        logger.error(f"RSI calculation error: {str(e)}")
        return 50.0, "Neutral", 0.0

def calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9):
    """Calculate MACD with comprehensive analysis."""
    try:
        if len(prices) < slow_period:
            logger.warning("Insufficient data for MACD calculation")
            return False, 0.0, "Neutral", 0.0

        price_series = pd.Series(prices)
        exp1 = price_series.ewm(span=fast_period, adjust=False).mean()
        exp2 = price_series.ewm(span=slow_period, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal

        # Calculate trend strength and direction
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]

        trend_direction = "Bullish" if current_hist > 0 else "Bearish"
        trend_strength = abs(current_hist) / price_series.mean()

        # Detect crossover
        crossover = "Bullish" if (prev_hist < 0 and current_hist > 0) else \
                   "Bearish" if (prev_hist > 0 and current_hist < 0) else "None"

        return (
            macd.iloc[-1] > signal.iloc[-1],  # Bullish signal
            abs(macd.iloc[-1] - signal.iloc[-1]),  # Signal strength
            crossover,  # Crossover type
            trend_strength  # Trend strength
        )
    except Exception as e:
        logger.error(f"MACD calculation error: {str(e)}")
        return False, 0.0, "None", 0.0

def calculate_fibonacci_levels(prices):
    """Calculate Fibonacci retracement and extension levels."""
    try:
        high = max(prices)
        low = min(prices)
        diff = high - low
        current = prices[-1]

        # Fibonacci ratios
        ratios = {
            'Extension 1.618': high + (diff * 0.618),
            'Extension 1.272': high + (diff * 0.272),
            'High': high,
            'Retracement 0.236': high - (diff * 0.236),
            'Retracement 0.382': high - (diff * 0.382),
            'Retracement 0.500': high - (diff * 0.500),
            'Retracement 0.618': high - (diff * 0.618),
            'Retracement 0.786': high - (diff * 0.786),
            'Low': low
        }

        # Find nearest levels
        levels_list = sorted([(v, k) for k, v in ratios.items()])
        current_position = None
        next_resistance = None
        next_support = None

        for i, (level, name) in enumerate(levels_list):
            if current > level:
                if i > 0:
                    current_position = name
                    if i < len(levels_list) - 1:
                        next_resistance = levels_list[i + 1]
                    next_support = levels_list[i - 1]
                break

        return {
            'levels': ratios,
            'current_position': current_position,
            'next_resistance': next_resistance,
            'next_support': next_support
        }

    except Exception as e:
        logger.error(f"Fibonacci calculation error: {str(e)}")
        return None

async def get_signal_analysis(token_id: str):
    """Generate comprehensive trading signal analysis."""
    logger.info(f"Starting signal analysis for token: {token_id}")
    try:
        prices = await get_historical_prices(token_id)
        if len(prices) < 90:
            logger.warning(f"Insufficient historical data: only {len(prices)} days available")
            raise ValueError("Insufficient historical data available for analysis")

        current_price = prices[-1]
        logger.info(f"Current price: ${current_price:,.2f}")

        # Calculate technical indicators with enhanced analysis
        current_rsi, rsi_trend, rsi_strength = calculate_rsi(prices)
        is_macd_bullish, macd_strength, macd_crossover, macd_trend_strength = calculate_macd(prices)

        # Calculate Fibonacci levels
        fib_levels = calculate_fibonacci_levels(prices)

        # Calculate support/resistance levels
        try:
            levels = calculate_support_resistance(prices)
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {str(e)}")
            levels = {
                'support_1': current_price * 0.95,
                'support_2': current_price * 0.90,
                'resistance_1': current_price * 1.05,
                'resistance_2': current_price * 1.10
            }

        # Get ML predictions
        try:
            ml_predictions = await ml_service.predict_price(prices, token_id)
            logger.info(f"Successfully generated ML predictions for {token_id}")
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
            ml_predictions=ml_predictions,
            rsi_trend=rsi_trend,
            rsi_strength=rsi_strength,
            macd_crossover=macd_crossover,
            macd_trend_strength=macd_trend_strength
        )

        # Calculate optimal trading levels
        optimal_levels = calculate_optimal_levels(
            current_price=current_price,
            levels=levels,
            signal_strength=signal_strength
        )

        # Build comprehensive response
        result = {
            'signal': get_signal_type(signal_strength),
            'signal_strength': abs(signal_strength),
            'trend_direction': "Bullish 📈" if signal_strength > 0 else "Bearish 📉" if signal_strength < 0 else "Neutral ⚖️",
            'current_price': current_price,
            'technical_indicators': {
                'rsi': {
                    'value': current_rsi,
                    'trend': rsi_trend,
                    'strength': rsi_strength
                },
                'macd': {
                    'signal': "Bullish 📈" if is_macd_bullish else "Bearish 📉",
                    'strength': macd_strength,
                    'crossover': macd_crossover,
                    'trend_strength': macd_trend_strength
                }
            },
            'fibonacci_levels': fib_levels,
            'price_levels': levels,
            'trading_levels': optimal_levels
        }

        # Add ML predictions if available
        if ml_predictions:
            result.update({
                'ml_predictions': ml_predictions,
                'confidence_score': ml_predictions['confidence_score']
            })

        logger.info("Successfully generated signal analysis")
        return result

    except Exception as e:
        logger.error(f"Failed to generate signal analysis: {str(e)}")
        raise

def calculate_enhanced_signal_strength(current_price, current_rsi, is_macd_bullish, macd_strength, levels, ml_predictions, rsi_trend, rsi_strength, macd_crossover, macd_trend_strength):
    """Calculate enhanced signal strength incorporating multiple indicators."""
    try:
        signal_strength = 0

        # RSI contribution (30%)
        if rsi_trend == "Oversold":
            signal_strength += 30 * rsi_strength
        elif rsi_trend == "Overbought":
            signal_strength -= 30 * rsi_strength

        # MACD contribution (30%)
        if is_macd_bullish:
            signal_strength += 30 * macd_trend_strength
        else:
            signal_strength -= 30 * macd_trend_strength

        # MACD Crossover bonus (10%)
        if macd_crossover == "Bullish":
            signal_strength += 10
        elif macd_crossover == "Bearish":
            signal_strength -= 10

        # Support/Resistance contribution (20%)
        if all(v > 0 for v in [levels['support_1'], levels['resistance_1']]):
            price_to_support1 = (current_price - levels['support_1']) / current_price
            price_to_resistance1 = (levels['resistance_1'] - current_price) / current_price

            if 0 <= price_to_support1 <= 0.05:  # Within 5% of support
                signal_strength += 20 * (1 - price_to_support1/0.05)
            elif 0 <= price_to_resistance1 <= 0.05:  # Within 5% of resistance
                signal_strength -= 20 * (1 - price_to_resistance1/0.05)

        # ML predictions influence (10%)
        if ml_predictions and 'next_day' in ml_predictions:
            try:
                rf_pred = float(ml_predictions['next_day']['rf_prediction'])
                prophet_pred = float(ml_predictions['next_day']['prophet_prediction'])
                confidence = min(ml_predictions['confidence_score'], 100) / 100

                # Calculate predicted changes
                rf_change = (rf_pred - current_price) / current_price
                prophet_change = (prophet_pred - current_price) / current_price

                # Weight the predictions based on confidence
                weighted_change = (rf_change + prophet_change) / 2 * confidence
                signal_strength += 10 * weighted_change
            except Exception as e:
                logger.error(f"Error processing ML predictions: {str(e)}")

        # Ensure signal strength stays within bounds
        return max(min(signal_strength, 100), -100)

    except Exception as e:
        logger.error(f"Error calculating signal strength: {str(e)}")
        return 0  # Return neutral signal on error

def calculate_optimal_levels(current_price, levels, signal_strength):
    """Calculate optimal entry and exit points based on price levels and signal strength."""
    try:
        support_1 = float(levels['support_1'])
        support_2 = float(levels['support_2'])
        resistance_1 = float(levels['resistance_1'])
        resistance_2 = float(levels['resistance_2'])

        # Calculate risk-reward ratios
        risk_reward_ratio = 2.5  # Minimum 2.5:1 reward-to-risk ratio
        volatility_factor = (resistance_1 - support_1) / current_price

        # Calculate optimal entry based on signal strength and support levels
        if signal_strength > 60:  # Strong buy signal
            optimal_entry = current_price  # Enter immediately
            stop_loss = max(support_2, current_price * 0.95)  # Max 5% loss
            # Ensure take profit is at least 2.5x the risk
            risk = current_price - stop_loss
            optimal_exit = current_price + (risk * risk_reward_ratio)
        elif signal_strength > 20:  # Moderate buy signal
            optimal_entry = (current_price + support_1) / 2  # Enter halfway to support
            stop_loss = support_2
            # Calculate minimum profit target
            risk = optimal_entry - stop_loss
            optimal_exit = optimal_entry + (risk * risk_reward_ratio)
        elif signal_strength < -60:  # Strong sell signal
            optimal_entry = resistance_2  # Wait for strong resistance
            stop_loss = resistance_2 * 1.02  # 2% above resistance
            optimal_exit = support_1  # Target first support
        elif signal_strength < -20:  # Moderate sell signal
            optimal_entry = resistance_1  # Wait for first resistance
            stop_loss = resistance_1 * 1.02
            optimal_exit = support_1
        else:  # Neutral
            optimal_entry = (current_price + support_1) / 2
            stop_loss = support_2
            risk = optimal_entry - stop_loss
            optimal_exit = optimal_entry + (risk * risk_reward_ratio)

        # Adjust exit based on volatility
        if signal_strength > 0:
            # For bullish signals, ensure exit is above resistance_1
            optimal_exit = max(optimal_exit, resistance_1 * (1 + volatility_factor))

        # Final validation to ensure proper order
        optimal_exit = max(optimal_exit, optimal_entry * 1.02)  # Minimum 2% profit
        stop_loss = min(stop_loss, optimal_entry * 0.98)  # Maximum 2% loss

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

def calculate_support_resistance(prices):
    """Calculate support and resistance levels using improved price clustering."""
    try:
        if len(prices) < 30:
            raise ValueError("Insufficient price data for support/resistance calculation")

        # Convert prices to numpy array and sort
        sorted_prices = np.sort(prices)
        price_range = sorted_prices[-1] - sorted_prices[0]
        current_price = prices[-1]

        # Dynamic clustering threshold based on price volatility
        volatility = np.std(prices) / np.mean(prices)
        cluster_threshold = price_range * min(max(0.01, volatility), 0.03)

        clusters = []
        current_cluster = [sorted_prices[0]]

        # Improved clustering algorithm
        for price in sorted_prices[1:]:
            if price - current_cluster[-1] <= cluster_threshold:
                current_cluster.append(price)
            else:
                if len(current_cluster) > len(prices) * 0.05:  # At least 5% of price points
                    cluster_mean = np.mean(current_cluster)
                    cluster_strength = len(current_cluster) / len(prices)
                    clusters.append((cluster_mean, cluster_strength))
                current_cluster = [price]

        # Add the last cluster if significant
        if len(current_cluster) > len(prices) * 0.05:
            cluster_mean = np.mean(current_cluster)
            cluster_strength = len(current_cluster) / len(prices)
            clusters.append((cluster_mean, cluster_strength))

        # Sort clusters by strength
        clusters.sort(key=lambda x: x[1], reverse=True)
        cluster_prices = [c[0] for c in clusters]

        # Separate support and resistance levels
        supports = [p for p in cluster_prices if p < current_price]
        resistances = [p for p in cluster_prices if p > current_price]

        # Ensure we have at least two levels for each
        if len(supports) < 2:
            # Calculate dynamic fallback levels based on volatility
            volatility_factor = max(0.05, min(0.15, volatility))
            if len(supports) == 0:
                supports = [
                    current_price * (1 - volatility_factor),
                    current_price * (1 - volatility_factor * 2)
                ]
            else:
                supports = [
                    supports[0],
                    supports[0] * (1 - volatility_factor)
                ]

        if len(resistances) < 2:
            volatility_factor = max(0.05, min(0.15, volatility))
            if len(resistances) == 0:
                resistances = [
                    current_price * (1 + volatility_factor),
                    current_price * (1 + volatility_factor * 2)
                ]
            else:
                resistances = [
                    resistances[0],
                    resistances[0] * (1 + volatility_factor)
                ]

        # Take the strongest levels
        support_levels = sorted(supports[-2:], reverse=True)
        resistance_levels = sorted(resistances[:2])

        return {
            "support_1": support_levels[0],
            "support_2": support_levels[1],
            "resistance_1": resistance_levels[0],
            "resistance_2": resistance_levels[1]
        }
    except Exception as e:
        logger.error(f"Support/Resistance calculation error: {str(e)}")
        # Fallback to simple percentage-based levels
        return {
            "support_1": current_price * 0.95,
            "support_2": current_price * 0.90,
            "resistance_1": current_price * 1.05,
            "resistance_2": current_price * 1.10
        }

def get_enhanced_dca_recommendation(signal_strength, ml_predictions, token_id):
    """Get enhanced DCA recommendation incorporating ML predictions."""
    base_recommendation = get_dca_recommendation(signal_strength)

    if not ml_predictions or 'next_day' not in ml_predictions:
        return base_recommendation

    confidence_score = ml_predictions['confidence_score']
    current_price = float(ml_predictions['next_day']['rf_prediction'])
    predicted_price = float(ml_predictions['next_day']['combined_prediction'])
    price_change = ((predicted_price - current_price) / current_price) * 100

    # Add ML-specific insights
    ml_insights = (
        f"\n\n💡 ML Analysis for {token_id.upper()}:\n"
        f"• Prediction Confidence: {confidence_score:.1f}%\n"
        f"• Expected Price: ${predicted_price:,.2f}\n"
        f"• Expected Range: ${ml_predictions['next_day']['lower_bound']:,.2f} "
        f"to ${ml_predictions['next_day']['upper_bound']:,.2f}\n"
        f"• Predicted Change: {price_change:+.2f}%\n"
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