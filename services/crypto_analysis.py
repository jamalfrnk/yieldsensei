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

            # Fill NaN values with appropriate methods
            df.fillna(method='ffill', inplace=True)
            df.fillna(method='bfill', inplace=True)

            return df

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            return df

    def get_market_summary(self, coin_id="bitcoin"):
        """Get current market summary for a cryptocurrency"""
        try:
            logger.debug(f"Fetching market summary for {coin_id}")
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'include_24hr_vol': True,
                'include_24hr_change': True,
                'include_market_cap': True
            }

            response = requests.get(url, params=params)
            response.raise_for_status()

            data = response.json()[coin_id]
            return {
                'current_price': data['usd'],
                'market_cap': data['usd_market_cap'],
                'volume': data['usd_24h_vol'],
                'price_change_24h': data['usd_24h_change'],
                'last_updated': datetime.now().isoformat()
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching market summary: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error processing market summary: {str(e)}")
            return None