import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from prophet import Prophet
import joblib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import fcntl
import json

# Configure logging
logger = logging.getLogger(__name__)

class MLPredictionService:
    def __init__(self):
        self.models: Dict[str, Dict] = {}  # Dictionary to store models per asset
        self.scalers: Dict[str, MinMaxScaler] = {}  # Dictionary to store scalers per asset
        self.model_path: str = 'models'

        # Create models directory if it doesn't exist
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)

    def prepare_features(self, prices: List[float], window_size: int = 14) -> pd.DataFrame:
        """Prepare features for ML model with improved validation."""
        try:
            if not isinstance(prices, (list, np.ndarray)) or len(prices) < window_size:
                raise ValueError(f"Prices must be a list/array with at least {window_size} elements")

            df = pd.DataFrame(prices, columns=['price'])

            # Technical indicators as features with error handling
            df['SMA'] = df['price'].rolling(window=window_size, min_periods=1).mean()
            df['STD'] = df['price'].rolling(window=window_size, min_periods=1).std()
            df['RSI'] = self._calculate_rsi(df['price'], window_size)
            df['MACD'] = self._calculate_macd(df['price'])

            # Price changes
            df['price_change'] = df['price'].pct_change()
            df['volatility'] = df['price_change'].rolling(window=window_size, min_periods=1).std()

            # Clean up NaN values
            df = df.fillna(method='bfill').fillna(method='ffill')

            # Verify no NaN values remain
            if df.isna().any().any():
                raise ValueError("Unable to clean all NaN values from features")

            return df
        except Exception as e:
            logger.error(f"Error preparing features: {str(e)}")
            raise

    def _calculate_rsi(self, prices: pd.Series, window_size: int = 14) -> pd.Series:
        """Calculate RSI with improved handling of edge cases."""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window_size, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window_size, min_periods=1).mean()

            # Handle division by zero
            rs = gain / loss.replace(0, float('inf'))
            rsi = 100 - (100 / (1 + rs))

            # Clean up outliers
            rsi = rsi.clip(0, 100)
            return rsi.fillna(50)  # Neutral RSI for any remaining NaN
        except Exception as e:
            logger.error(f"RSI calculation error: {str(e)}")
            return pd.Series([50] * len(prices))  # Return neutral RSI on error

    def _calculate_macd(self, prices: pd.Series) -> pd.Series:
        """Calculate MACD with robust error handling."""
        try:
            exp1 = prices.ewm(span=12, adjust=False).mean()
            exp2 = prices.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            return macd.fillna(0)  # Fill any NaN with 0
        except Exception as e:
            logger.error(f"MACD calculation error: {str(e)}")
            return pd.Series([0] * len(prices))  # Return 0 on error

    def train_models(self, historical_prices: List[float], asset_id: str) -> bool:
        """Train both Random Forest and Prophet models with improved robustness."""
        lock_path = f"{self.model_path}/model_lock_{asset_id}"
        try:
            self._acquire_lock(lock_path)
            logger.info(f"Starting model training for asset: {asset_id}")

            if len(historical_prices) < 30:
                raise ValueError("Insufficient historical data for training")

            # Prepare data for Random Forest
            df = self.prepare_features(historical_prices)
            X = df.drop(['price', 'price_change'], axis=1)
            y = df['price'].shift(-1)  # Predict next day's price
            X = X[:-1]  # Remove last row as we don't have next day's price for it
            y = y[:-1]

            # Initialize and fit scaler
            scaler = MinMaxScaler()
            X_scaled = scaler.fit_transform(X)

            # Train Random Forest model with optimized parameters
            rf_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            rf_model.fit(X_scaled, y)

            # Prepare data for Prophet
            prophet_df = pd.DataFrame({
                'ds': pd.date_range(end=datetime.now(), periods=len(historical_prices)),
                'y': historical_prices
            })

            # Configure Prophet for crypto market characteristics
            prophet_model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=True,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10,
                seasonality_mode='multiplicative'
            )
            prophet_model.fit(prophet_df)

            # Save models and scaler
            model_paths = self._get_model_paths(asset_id)
            joblib.dump(rf_model, model_paths['rf_model'])
            prophet_model.save(model_paths['prophet_model'])
            joblib.dump(scaler, model_paths['scaler'])

            # Store in memory
            self.models[asset_id] = {
                'rf_model': rf_model,
                'prophet_model': prophet_model
            }
            self.scalers[asset_id] = scaler

            logger.info(f"Model training completed successfully for asset: {asset_id}")
            return True

        except Exception as e:
            logger.error(f"Error training models for asset {asset_id}: {str(e)}")
            return False
        finally:
            self._release_lock()

    def _get_model_paths(self, asset_id: str) -> Dict[str, str]:
        """Get asset-specific model file paths."""
        return {
            'rf_model': f'{self.model_path}/rf_model_{asset_id}.joblib',
            'prophet_model': f'{self.model_path}/prophet_{asset_id}.json',
            'scaler': f'{self.model_path}/scaler_{asset_id}.joblib'
        }

    def _acquire_lock(self, lock_path: str) -> None:
        """Acquire a file lock for thread-safe operations."""
        self.lock_file = open(lock_path, 'w')
        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX)

    def _release_lock(self) -> None:
        """Release the file lock."""
        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
        self.lock_file.close()

    def _load_models(self, asset_id: str) -> bool:
        """Load asset-specific models with improved error handling."""
        try:
            model_paths = self._get_model_paths(asset_id)

            if os.path.exists(model_paths['rf_model']):
                rf_model = joblib.load(model_paths['rf_model'])
                scaler = joblib.load(model_paths['scaler'])

                prophet_model = Prophet(
                    yearly_seasonality=True,
                    weekly_seasonality=True,
                    daily_seasonality=True,
                    changepoint_prior_scale=0.05,
                    seasonality_prior_scale=10,
                    seasonality_mode='multiplicative'
                )
                prophet_model.load(model_paths['prophet_model'])

                self.models[asset_id] = {
                    'rf_model': rf_model,
                    'prophet_model': prophet_model
                }
                self.scalers[asset_id] = scaler
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading models for asset {asset_id}: {str(e)}")
            return False

    async def predict_price(self, historical_prices: List[float], asset_id: str, days_ahead: int = 7) -> Optional[Dict]:
        """Generate price predictions with improved robustness."""
        try:
            if not isinstance(historical_prices, (list, np.ndarray)) or len(historical_prices) < 14:
                raise ValueError("Invalid historical prices data")

            # Check if models exist for this asset
            if asset_id not in self.models:
                if not self._load_models(asset_id):
                    # Train new models if they don't exist
                    if not self.train_models(historical_prices, asset_id):
                        raise Exception("Failed to train models")

            predictions = {}
            current_price = historical_prices[-1]

            # Random Forest predictions
            df = self.prepare_features(historical_prices)
            X = df.drop(['price', 'price_change'], axis=1)
            X_scaled = self.scalers[asset_id].transform(X)
            rf_pred = self.models[asset_id]['rf_model'].predict(X_scaled[-1].reshape(1, -1))[0]

            # Prophet predictions
            prophet_df = pd.DataFrame({
                'ds': pd.date_range(end=datetime.now(), periods=len(historical_prices)),
                'y': historical_prices
            })
            future_dates = pd.DataFrame({
                'ds': pd.date_range(start=datetime.now(), periods=days_ahead)
            })
            prophet_forecast = self.models[asset_id]['prophet_model'].predict(future_dates)

            # Calculate prediction intervals
            prophet_std = prophet_forecast['yhat'].std()
            prophet_pred = float(prophet_forecast['yhat'].iloc[0])

            # Combine predictions with confidence intervals
            combined_pred = (rf_pred + prophet_pred) / 2
            prediction_std = abs(rf_pred - prophet_pred) / 2

            # Calculate prediction bounds
            lower_bound = combined_pred - 2 * prediction_std
            upper_bound = combined_pred + 2 * prediction_std

            # Ensure bounds are reasonable
            lower_bound = max(lower_bound, current_price * 0.5)  # Max 50% drop
            upper_bound = min(upper_bound, current_price * 2.0)  # Max 100% gain

            predictions['next_day'] = {
                'rf_prediction': float(rf_pred),
                'prophet_prediction': prophet_pred,
                'combined_prediction': combined_pred,
                'lower_bound': lower_bound,
                'upper_bound': upper_bound
            }

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                current_price,
                rf_pred,
                prophet_pred,
                lower_bound,
                upper_bound
            )

            predictions['confidence_score'] = confidence_score
            predictions['forecast'] = {
                'dates': prophet_forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
                'values': prophet_forecast['yhat'].tolist(),
                'lower_bounds': prophet_forecast['yhat_lower'].tolist(),
                'upper_bounds': prophet_forecast['yhat_upper'].tolist()
            }

            return predictions

        except Exception as e:
            logger.error(f"Error generating predictions for asset {asset_id}: {str(e)}")
            return None

    def _calculate_confidence_score(
        self,
        current_price: float,
        rf_pred: float,
        prophet_pred: float,
        lower_bound: float,
        upper_bound: float
    ) -> float:
        """Calculate a confidence score for the predictions."""
        try:
            # Calculate prediction agreement
            pred_diff = abs(rf_pred - prophet_pred) / current_price
            pred_agreement = max(0, 100 * (1 - pred_diff))

            # Calculate prediction range confidence
            range_size = (upper_bound - lower_bound) / current_price
            range_confidence = max(0, 100 * (1 - range_size))

            # Calculate trend consistency
            rf_trend = rf_pred > current_price
            prophet_trend = prophet_pred > current_price
            trend_agreement = 100 if rf_trend == prophet_trend else 0

            # Combine scores with weighted average
            confidence_score = (
                0.4 * pred_agreement +
                0.4 * range_confidence +
                0.2 * trend_agreement
            )

            return min(100, max(0, confidence_score))

        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 50  # Return neutral confidence on error

# Initialize global ML service instance
ml_service = MLPredictionService()