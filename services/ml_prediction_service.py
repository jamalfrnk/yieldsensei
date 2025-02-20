import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from prophet import Prophet
from joblib import dump, load
import os
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class MLPredictionService:
    def __init__(self):
        self.rf_model = None
        self.prophet_model = None
        self.scaler = MinMaxScaler()
        self.model_path = 'models'
        
        # Create models directory if it doesn't exist
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)

    def prepare_features(self, prices, window_size=14):
        """Prepare features for ML model."""
        df = pd.DataFrame(prices, columns=['price'])
        
        # Technical indicators as features
        df['SMA'] = df['price'].rolling(window=window_size).mean()
        df['STD'] = df['price'].rolling(window=window_size).std()
        df['RSI'] = self._calculate_rsi(df['price'], window_size)
        df['MACD'] = self._calculate_macd(df['price'])
        
        # Price changes
        df['price_change'] = df['price'].pct_change()
        df['volatility'] = df['price_change'].rolling(window=window_size).std()
        
        # Remove NaN values
        df = df.dropna()
        
        return df

    def _calculate_rsi(self, prices, window_size=14):
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window_size).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window_size).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, prices):
        """Calculate MACD."""
        exp1 = prices.ewm(span=12, adjust=False).mean()
        exp2 = prices.ewm(span=26, adjust=False).mean()
        return exp1 - exp2

    def train_models(self, historical_prices):
        """Train both Random Forest and Prophet models."""
        try:
            logger.info("Starting model training")
            
            # Prepare data for Random Forest
            df = self.prepare_features(historical_prices)
            X = df.drop(['price', 'price_change'], axis=1)
            y = df['price'].shift(-1)  # Predict next day's price
            X = X[:-1]  # Remove last row as we don't have next day's price for it
            y = y[:-1]
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train Random Forest model
            self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.rf_model.fit(X_scaled, y)
            
            # Save Random Forest model
            dump(self.rf_model, f'{self.model_path}/rf_model.joblib')
            dump(self.scaler, f'{self.model_path}/scaler.joblib')
            
            # Prepare data for Prophet
            prophet_df = pd.DataFrame({
                'ds': pd.date_range(end=datetime.now(), periods=len(historical_prices)),
                'y': historical_prices
            })
            
            # Train Prophet model
            self.prophet_model = Prophet(yearly_seasonality=True, weekly_seasonality=True)
            self.prophet_model.fit(prophet_df)
            
            # Save Prophet model
            self.prophet_model.save(f'{self.model_path}/prophet_model.json')
            
            logger.info("Model training completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error training models: {str(e)}")
            return False

    async def predict_price(self, historical_prices, days_ahead=7):
        """Generate price predictions using both models."""
        try:
            predictions = {}
            
            # Random Forest predictions
            df = self.prepare_features(historical_prices)
            X = df.drop(['price', 'price_change'], axis=1)
            X_scaled = self.scaler.transform(X)
            rf_pred = self.rf_model.predict(X_scaled[-1].reshape(1, -1))[0]
            
            # Prophet predictions
            prophet_df = pd.DataFrame({
                'ds': pd.date_range(end=datetime.now(), periods=len(historical_prices)),
                'y': historical_prices
            })
            future_dates = self.prophet_model.make_future_dataframe(periods=days_ahead)
            prophet_forecast = self.prophet_model.predict(future_dates)
            
            # Get predictions and confidence intervals
            predictions['next_day'] = {
                'rf_prediction': float(rf_pred),
                'prophet_prediction': float(prophet_forecast['yhat'].iloc[-1]),
                'lower_bound': float(prophet_forecast['yhat_lower'].iloc[-1]),
                'upper_bound': float(prophet_forecast['yhat_upper'].iloc[-1])
            }
            
            # Calculate confidence score (0-100)
            confidence_score = self._calculate_confidence_score(
                historical_prices[-1],
                rf_pred,
                prophet_forecast['yhat'].iloc[-1],
                prophet_forecast['yhat_lower'].iloc[-1],
                prophet_forecast['yhat_upper'].iloc[-1]
            )
            
            predictions['confidence_score'] = confidence_score
            predictions['forecast'] = {
                'dates': prophet_forecast['ds'].tail(days_ahead).dt.strftime('%Y-%m-%d').tolist(),
                'values': prophet_forecast['yhat'].tail(days_ahead).tolist(),
                'lower_bounds': prophet_forecast['yhat_lower'].tail(days_ahead).tolist(),
                'upper_bounds': prophet_forecast['yhat_upper'].tail(days_ahead).tolist()
            }
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error generating predictions: {str(e)}")
            return None

    def _calculate_confidence_score(self, current_price, rf_pred, prophet_pred, lower_bound, upper_bound):
        """Calculate a confidence score for the predictions."""
        # Calculate prediction agreement
        pred_diff = abs(rf_pred - prophet_pred) / current_price
        pred_agreement = max(0, 100 * (1 - pred_diff))
        
        # Calculate prediction range confidence
        range_size = (upper_bound - lower_bound) / current_price
        range_confidence = max(0, 100 * (1 - range_size))
        
        # Combine scores (weighted average)
        confidence_score = (0.6 * pred_agreement + 0.4 * range_confidence)
        return min(100, max(0, confidence_score))

# Initialize global ML service instance
ml_service = MLPredictionService()
