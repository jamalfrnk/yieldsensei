import logging
import numpy as np
import pandas as pd
from typing import Dict, Tuple
from services.ml_prediction_service import ml_service

# Configure logging
logger = logging.getLogger(__name__)

async def get_historical_prices(token_id: str) -> np.ndarray:
    """Fetch historical price data."""
    try:
        prices = await ml_service.get_token_prices(token_id, days=90)
        return np.array(prices)
    except Exception as e:
        logger.error(f"Error fetching historical prices: {str(e)}")
        raise

def calculate_rsi(prices: np.ndarray, periods: int = 14) -> Tuple[float, str]:
    """Calculate RSI using standard method."""
    try:
        if len(prices) < periods + 1:
            return 50.0, "Neutral"

        # Calculate price changes
        delta = np.diff(prices)
        gains = delta.copy()
        losses = delta.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)

        # Calculate average gains and losses
        avg_gain = np.mean(gains[:periods])
        avg_loss = np.mean(losses[:periods])

        for i in range(periods, len(delta)):
            avg_gain = (avg_gain * (periods - 1) + gains[i]) / periods
            avg_loss = (avg_loss * (periods - 1) + losses[i]) / periods

        if avg_loss == 0:
            return 100.0, "Overbought"

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Determine trend
        if rsi > 70:
            trend = "Overbought"
        elif rsi < 30:
            trend = "Oversold"
        else:
            trend = "Neutral"

        return float(rsi), trend

    except Exception as e:
        logger.error(f"RSI calculation error: {str(e)}")
        return 50.0, "Neutral"

def calculate_support_resistance(prices: np.ndarray) -> Dict[str, float]:
    """Calculate basic support and resistance levels."""
    try:
        if len(prices) < 30:
            raise ValueError("Insufficient price data")

        current_price = prices[-1]
        sorted_prices = np.sort(prices)

        # Simple support and resistance calculation
        support_1 = np.percentile(sorted_prices, 25)
        support_2 = np.percentile(sorted_prices, 10)
        resistance_1 = np.percentile(sorted_prices, 75)
        resistance_2 = np.percentile(sorted_prices, 90)

        return {
            "support_1": float(support_1),
            "support_2": float(support_2),
            "resistance_1": float(resistance_1),
            "resistance_2": float(resistance_2)
        }

    except Exception as e:
        logger.error(f"Support/Resistance calculation error: {str(e)}")
        # Fallback to percentage-based levels
        current_price = prices[-1]
        return {
            "support_1": current_price * 0.95,
            "support_2": current_price * 0.90,
            "resistance_1": current_price * 1.05,
            "resistance_2": current_price * 1.10
        }

async def get_signal_analysis(token_id: str) -> Dict:
    """Generate basic trading signal analysis."""
    try:
        prices = await get_historical_prices(token_id)
        current_price = prices[-1]

        # Calculate indicators
        rsi_value, rsi_trend = calculate_rsi(prices)
        levels = calculate_support_resistance(prices)

        # Determine basic signal
        signal = "Neutral"
        if rsi_value > 70:
            signal = "Sell"
        elif rsi_value < 30:
            signal = "Buy"

        signal_strength = abs(50 - rsi_value)

        return {
            "current_price": current_price,
            "signal": signal,
            "rsi": rsi_value,
            "rsi_trend": rsi_trend,
            "signal_strength": signal_strength,
            **levels
        }

    except Exception as e:
        logger.error(f"Signal analysis error: {str(e)}")
        raise