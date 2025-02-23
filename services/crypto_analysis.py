import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import logging
import ta

logger = logging.getLogger(__name__)

class CryptoAnalysisService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        logger.info("Initializing CryptoAnalysisService with CoinGecko API")
        self._test_api_connection()

    def _test_api_connection(self):
        """Test the API connection during initialization"""
        try:
            response = requests.get(f"{self.base_url}/ping")
            response.raise_for_status()
            logger.info("Successfully connected to CoinGecko API")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to CoinGecko API: {str(e)}")
            raise ConnectionError("Cannot connect to CoinGecko API")

    def get_historical_data(self, coin_id="bitcoin", days=90):
        """Fetch historical price data for a cryptocurrency"""
        try:
            logger.debug(f"Fetching historical data for {coin_id}")
            url = f"{self.base_url}/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily'
            }
            response = requests.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            logger.debug(f"Successfully fetched historical data for {coin_id}")
            return self._add_technical_indicators(df)

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching historical data: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error processing historical data: {str(e)}")
            return None

    def _add_technical_indicators(self, df):
        """Add technical indicators to the dataframe"""
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

    def get_market_summary(self, coin_id="bitcoin"):
        """Get current market summary for a cryptocurrency"""
        try:
            logger.debug(f"Fetching market summary for {coin_id}")
            url = f"{self.base_url}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }

            response = requests.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            market_data = data['market_data']

            summary = {
                'current_price': market_data['current_price']['usd'],
                'market_cap': market_data['market_cap']['usd'],
                'volume': market_data['total_volume']['usd'],
                'price_change_24h': market_data['price_change_percentage_24h'],
                'last_updated': data['last_updated']
            }

            logger.debug(f"Successfully fetched market summary for {coin_id}")
            return summary

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching market summary: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error processing market summary: {str(e)}")
            return None