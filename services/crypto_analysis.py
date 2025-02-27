import logging
from typing import Optional, Dict, Any, List
import asyncio
import aiohttp
from datetime import datetime, timedelta
import json
from services.birdeye_service import get_historical_data, get_token_price, get_token_market_data

# Configure logging
logger = logging.getLogger(__name__)

# Initialize optional dependencies with error handling
try:
    import pandas as pd
    import numpy as np
    import ta
    HAVE_ANALYTICS = True
except ImportError as e:
    logger.warning(f"Analytics dependencies not available: {str(e)}")
    HAVE_ANALYTICS = False

class CryptoAnalysisService:
    def __init__(self):
        self.base_url = "https://public-api.birdeye.so"
        logger.info("Initializing CryptoAnalysisService with BirdEye API")
        try:
            self._test_api_connection()
        except Exception as e:
            logger.error(f"Failed to initialize CryptoAnalysisService: {str(e)}")
            # Don't raise the error, allow the service to initialize with degraded functionality
            pass

    async def _test_api_connection_async(self):
        """Test the API connection asynchronously"""
        async with aiohttp.ClientSession() as session:
            try:
                headers = {"X-API-KEY": "a2f6b375cc2c4afbb5fdb456d7bdc4ff"}
                # Test with a simple token metadata request for SOL
                url = f"{self.base_url}/defi/token_metadata"
                params = {"address": "So11111111111111111111111111111111111111112"}
                
                async with session.get(url, params=params, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data.get('success') == True:
                        logger.info("Successfully connected to BirdEye API")
                        return True
                    else:
                        raise ConnectionError(f"BirdEye API error: {data.get('message', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Failed to connect to BirdEye API: {str(e)}")
                raise ConnectionError(f"Cannot connect to BirdEye API: {str(e)}")

    def _test_api_connection(self):
        """Test the API connection during initialization (synchronous wrapper)"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._test_api_connection_async())

    def get_historical_data(self, coin_id="bitcoin", days=90):
        """Fetch historical price data for a cryptocurrency using BirdEye API"""
        if not HAVE_ANALYTICS:
            logger.warning("Analytics features not available - missing required packages")
            return pd.DataFrame()

        try:
            logger.debug(f"Fetching historical data for {coin_id}")
            
            # Use the imported function from birdeye_service
            df = get_historical_data(coin_id, days)
            
            if df.empty:
                logger.warning(f"No historical data available for {coin_id}")
                return pd.DataFrame()
            
            # Apply technical indicators if data is available
            df = self._add_technical_indicators(df)
            
            logger.debug(f"Successfully fetched {len(df)} price points for {coin_id}")
            return df

        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return pd.DataFrame()  # Return empty DataFrame on error

    def _add_technical_indicators(self, df):
        """Add technical indicators to the dataframe"""
        if not HAVE_ANALYTICS:
            logger.warning("Analytics features not available - skipping technical indicator calculation")
            return df
        try:
            logger.debug("Calculating technical indicators")
            # Calculate RSI
            df['rsi'] = ta.momentum.RSIIndicator(close=df['price']).rsi()

            # Calculate MACD
            macd = ta.trend.MACD(close=df['price'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()

            # Calculate Bollinger Bands
            bollinger = ta.volatility.BollingerBands(close=df['price'])
            df['bb_high'] = bollinger.bollinger_hband()
            df['bb_low'] = bollinger.bollinger_lband()
            df['bb_mid'] = bollinger.bollinger_mavg()

            # Support and Resistance Levels
            df['support_1'] = df['price'].rolling(window=10).min()
            df['support_2'] = df['price'].rolling(window=20).min()
            df['resistance_1'] = df['price'].rolling(window=10).max()
            df['resistance_2'] = df['price'].rolling(window=20).max()

            # Fill NaN values with forward fill then backward fill
            df = df.ffill().bfill()
            logger.debug("Successfully calculated technical indicators")
            return df

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            return df

    async def get_market_summary_async(self, coin_id="bitcoin"):
        """Get current market summary for a cryptocurrency using BirdEye API (async)"""
        try:
            logger.debug(f"Fetching market summary for {coin_id}")
            
            # Use the imported function from birdeye_service
            market_data = await get_token_market_data(coin_id)
            
            # Get the current price
            price_data = await get_token_price(coin_id)
            
            summary = {
                'current_price': price_data.get('usd', 0.0),
                'market_cap': market_data.get('market_cap', 0),
                'volume': market_data.get('total_volume', 0),
                'price_change_24h': market_data.get('price_change_percentage_24h', 0.0),
                'last_updated': datetime.now().isoformat(),
                'high_24h': market_data.get('high_24h', 0.0),
                'low_24h': market_data.get('low_24h', 0.0)
            }

            logger.debug(f"Successfully fetched market summary for {coin_id}")
            return summary

        except Exception as e:
            logger.error(f"Error processing market summary: {str(e)}")
            # Return default values instead of None
            return {
                'current_price': 0.0,
                'market_cap': 0,
                'volume': 0,
                'price_change_24h': 0.0,
                'high_24h': 0.0,
                'low_24h': 0.0,
                'last_updated': datetime.now().isoformat()
            }
            
    def get_market_summary(self, coin_id="bitcoin"):
        """Synchronous wrapper for get_market_summary_async"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_market_summary_async(coin_id))

    def get_market_sentiment(self, coin_id="bitcoin"):
        """Get market sentiment analysis"""
        if not HAVE_ANALYTICS:
            logger.warning("Analytics features not available - skipping market sentiment analysis")
            return None
        try:
            logger.debug(f"Analyzing market sentiment for {coin_id}")
            df = self.get_historical_data(coin_id)
            if df is None or df.empty: #handle empty dataframe returned from get_historical_data
                return None

            # Calculate sentiment score based on technical indicators
            rsi = df['rsi'].iloc[-1]
            macd = df['macd'].iloc[-1]
            macd_signal = df['macd_signal'].iloc[-1]
            price = df['price'].iloc[-1]
            sma_20 = df['price'].rolling(window=20).mean().iloc[-1]

            # Initialize sentiment factors
            factors = []
            score = 0.5  # Neutral starting point

            # RSI Analysis
            if rsi > 70:
                factors.append("RSI indicates overbought conditions")
                score -= 0.1
            elif rsi < 30:
                factors.append("RSI indicates oversold conditions")
                score += 0.1

            # MACD Analysis
            if macd > macd_signal:
                factors.append("MACD shows bullish momentum")
                score += 0.1
            else:
                factors.append("MACD shows bearish momentum")
                score -= 0.1

            # Trend Analysis
            if price > sma_20:
                factors.append("Price above 20-day moving average")
                score += 0.1
            else:
                factors.append("Price below 20-day moving average")
                score -= 0.1

            # Normalize score between 0 and 1
            score = max(0, min(1, score))

            # Determine sentiment label
            if score > 0.6:
                label = "Bullish 📈"
            elif score < 0.4:
                label = "Bearish 📉"
            else:
                label = "Neutral ⚖️"

            sentiment_data = {
                'score': score,
                'label': label,
                'factors': factors
            }

            logger.debug(f"Successfully generated sentiment analysis for {coin_id}")
            return sentiment_data

        except Exception as e:
            logger.error(f"Error calculating market sentiment: {str(e)}")
            return None

    def get_dca_recommendations(self, coin_id="bitcoin"):
        """Get DCA (Dollar Cost Averaging) recommendations"""
        if not HAVE_ANALYTICS:
            logger.warning("Analytics features not available - skipping DCA recommendations")
            return None
        try:
            logger.debug(f"Generating DCA recommendations for {coin_id}")
            signal_data = get_signal_analysis(coin_id)

            if not signal_data:
                return None

            current_price = signal_data['current_price']
            support_1 = signal_data['price_levels']['support_1']
            support_2 = signal_data['price_levels']['support_2']

            # Calculate entry points based on technical levels
            entry_points = [
                {'price': current_price * 0.98, 'allocation': '20%'},
                {'price': support_1, 'allocation': '40%'},
                {'price': support_2, 'allocation': '40%'}
            ]

            # Determine risk level based on signal strength
            signal_strength = abs(signal_data['signal_strength'])
            if signal_strength > 70:
                risk_level = "High Risk 🔴"
                risk_explanation = "Strong market momentum detected. Consider smaller position sizes."
            elif signal_strength > 30:
                risk_level = "Medium Risk 🟡"
                risk_explanation = "Moderate market conditions. Standard position sizing recommended."
            else:
                risk_level = "Low Risk 🟢"
                risk_explanation = "Stable market conditions. Optimal for DCA strategy."

            # Generate schedule based on risk level
            if risk_level == "High Risk 🔴":
                schedule = "Weekly small purchases spread across 6-8 weeks"
            elif risk_level == "Medium Risk 🟡":
                schedule = "Bi-weekly purchases spread across 4-6 weeks"
            else:
                schedule = "Monthly purchases spread across 3-4 months"

            recommendations = {
                'entry_points': entry_points,
                'risk_level': risk_level,
                'risk_explanation': risk_explanation,
                'schedule': schedule
            }

            logger.debug(f"Successfully generated DCA recommendations for {coin_id}")
            return recommendations

        except Exception as e:
            logger.error(f"Error generating DCA recommendations: {str(e)}")
            return None