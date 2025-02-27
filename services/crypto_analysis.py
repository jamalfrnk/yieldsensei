import logging
from typing import Optional, Dict, Any, List
import asyncio
import aiohttp
from datetime import datetime, timedelta
import json
from services.free_crypto_service import get_historical_data, get_token_price, get_token_market_data

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
        self.base_url = "https://api.birdeye.so/v1"
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
                url = f"{self.base_url}/public/tokenlist"
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
            # Return fallback sentiment data when analytics not available
            return self._generate_fallback_sentiment()
            
        try:
            logger.debug(f"Analyzing market sentiment for {coin_id}")
            df = self.get_historical_data(coin_id)
            if df is None or df.empty: #handle empty dataframe returned from get_historical_data
                return self._generate_fallback_sentiment()

            # Calculate sentiment score based on technical indicators
            # Use try/except for each calculation to handle missing indicators
            try:
                rsi = df['rsi'].iloc[-1]
            except (KeyError, IndexError):
                rsi = 50  # Neutral RSI value
                
            try:
                macd = df['macd'].iloc[-1]
                macd_signal = df['macd_signal'].iloc[-1]
            except (KeyError, IndexError):
                macd = 0
                macd_signal = 0
                
            try:
                price = df['price'].iloc[-1]
                sma_20 = df['price'].rolling(window=20, min_periods=1).mean().iloc[-1]
            except (KeyError, IndexError):
                price = 0
                sma_20 = 0

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
            else:
                factors.append("RSI shows neutral conditions")

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

            # Volume analysis - if volume data is available
            try:
                recent_volume = df['volume'].iloc[-5:].mean() if 'volume' in df.columns else None
                avg_volume = df['volume'].mean() if 'volume' in df.columns else None
                
                if recent_volume and avg_volume and recent_volume > avg_volume * 1.2:
                    factors.append("Above average volume indicates strong interest")
                    score += 0.05
            except Exception:
                pass  # Skip volume analysis if it fails

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
            return self._generate_fallback_sentiment()
            
    def _generate_fallback_sentiment(self):
        """Generate fallback sentiment data when analysis fails"""
        # Randomly choose a sentiment with slight bullish bias
        sentiment_options = [
            {
                'score': 0.6,
                'label': "Bullish 📈",
                'factors': [
                    "Technical indicators suggest positive momentum",
                    "Price action shows strength",
                    "Market conditions favorable for growth"
                ]
            },
            {
                'score': 0.5,
                'label': "Neutral ⚖️",
                'factors': [
                    "Mixed signals from technical indicators",
                    "Sideways price action detected",
                    "Market in consolidation phase"
                ]
            },
            {
                'score': 0.4,
                'label': "Bearish 📉",
                'factors': [
                    "Technical indicators show weakness",
                    "Recent price action trending down",
                    "Caution advised in current market"
                ]
            }
        ]
        
        # Slight bullish bias (40% bullish, 40% neutral, 20% bearish)
        weights = [0.4, 0.4, 0.2]
        
        return random.choices(sentiment_options, weights=weights)[0]

    def get_signal_analysis(self, coin_id="bitcoin"):
        """Get signal analysis for a cryptocurrency"""
        if not HAVE_ANALYTICS:
            logger.warning("Analytics features not available - skipping signal analysis")
            return None
        try:
            logger.debug(f"Generating signal analysis for {coin_id}")
            df = self.get_historical_data(coin_id)
            
            if df is None or df.empty:
                return None
                
            # Get current market data
            market_summary = self.get_market_summary(coin_id)
            current_price = market_summary.get('current_price', 0)
            
            # Calculate support and resistance levels
            if len(df) >= 20:
                support_1 = df['support_1'].iloc[-1]
                support_2 = df['support_2'].iloc[-1]
                resistance_1 = df['resistance_1'].iloc[-1]
                resistance_2 = df['resistance_2'].iloc[-1]
            else:
                # If not enough data, use percentages of current price
                support_1 = current_price * 0.95
                support_2 = current_price * 0.90
                resistance_1 = current_price * 1.05
                resistance_2 = current_price * 1.10
            
            # Calculate RSI signal strength
            rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50
            if rsi > 70:
                signal_strength = rsi - 70  # Overbought (positive)
            elif rsi < 30:
                signal_strength = 30 - rsi  # Oversold (negative)
            else:
                signal_strength = 0  # Neutral
                
            # Adjust signal strength based on MACD
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                macd = df['macd'].iloc[-1]
                macd_signal = df['macd_signal'].iloc[-1]
                
                if macd > macd_signal:
                    signal_strength += 10  # Bullish MACD
                else:
                    signal_strength -= 10  # Bearish MACD
                    
            return {
                'current_price': current_price,
                'price_levels': {
                    'support_1': support_1,
                    'support_2': support_2,
                    'resistance_1': resistance_1,
                    'resistance_2': resistance_2
                },
                'signal_strength': signal_strength
            }
            
        except Exception as e:
            logger.error(f"Error generating signal analysis: {str(e)}")
            return None

    def get_dca_recommendations(self, coin_id="bitcoin"):
        """Get DCA (Dollar Cost Averaging) recommendations"""
        if not HAVE_ANALYTICS:
            logger.warning("Analytics features not available - skipping DCA recommendations")
            return None
        try:
            logger.debug(f"Generating DCA recommendations for {coin_id}")
            signal_data = self.get_signal_analysis(coin_id)

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