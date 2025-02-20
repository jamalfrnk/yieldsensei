import os
from flask import Flask, render_template, request, jsonify
import asyncio
from services.technical_analysis import get_signal_analysis
from services.coingecko_service import get_token_price, get_token_market_data
from services.ml_prediction_service import ml_service
import logging
from datetime import datetime, timedelta
from flask_talisman import Talisman
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from models import db, Quiz, Question, UserProgress, User

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Default data for the dashboard
DEFAULT_DATA = {
    'token_symbol': 'Enter a token',
    'price': 0.0,
    'price_change': 0.0,
    'signal_strength': 0,
    'signal_description': 'Enter a token to analyze',
    'trend_direction': 'Neutral ⚖️',
    'rsi': 50,
    'support_1': 0.0,
    'support_2': 0.0,
    'resistance_1': 0.0,
    'resistance_2': 0.0,
    'optimal_entry': 0.0,  # Added default
    'optimal_exit': 0.0,   # Added default
    'stop_loss': 0.0,      # Added default
    'dca_recommendation': 'Enter a token to get DCA recommendations',
    'historical_data': [],
    'predictions': None,
    'confidence_score': 0
}

def create_app():
    app = Flask(__name__)

    # Enable CORS with proper configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST"],
            "allow_headers": ["Content-Type"]
        }
    })

    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # Security headers
    Talisman(app,
        content_security_policy={
            'default-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", 'cdn.jsdelivr.net', '*'],
            'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", 'cdn.jsdelivr.net'],
            'style-src': ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net'],
            'img-src': ["'self'", 'data:', 'cdn.jsdelivr.net', '*'],
            'font-src': ["'self'", 'cdn.jsdelivr.net'],
            'connect-src': ["'self'", '*']
        },
        force_https=False
    )

    # Enable compression
    Compress(app)

    # Configure rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour"]
    )

    @app.route('/')
    @limiter.exempt
    async def index():
        """Render the main dashboard."""
        logger.info("Rendering index page")
        return render_template('dashboard.html', **DEFAULT_DATA)

    @app.route('/search')
    @limiter.limit("20 per minute")
    async def search():
        """Handle token search and analysis."""
        token = request.args.get('token', 'bitcoin').lower()
        try:
            logger.info(f"Processing search request for token: {token}")

            # Get market data and signal analysis
            price_data = await get_token_price(token)
            signal_data = await get_signal_analysis(token)
            market_data = await get_token_market_data(token)

            if not market_data or not price_data or not signal_data:
                raise ValueError("Unable to fetch complete market data for the token")

            logger.info(f"Retrieved data for {token}: Price=${price_data['usd']}, Signal strength={signal_data['signal_strength']}")

            # Extract historical price data
            historical_prices = []
            if 'prices' in market_data and market_data['prices']:
                historical_prices = market_data['prices']
                logger.info(f"Found {len(historical_prices)} historical price points")

                try:
                    # Train ML models with historical data if not already trained
                    price_values = [price[1] for price in historical_prices]
                    if not ml_service.rf_model or not ml_service.prophet_model:
                        ml_service.train_models(price_values)

                    # Get price predictions
                    predictions = await ml_service.predict_price(price_values)
                    logger.info("Generated ML predictions successfully")

                    # Calculate all necessary template data
                    template_data = {
                        'token_symbol': token.upper(),
                        'price': float(price_data['usd']),
                        'price_change': float(price_data['usd_24h_change']),
                        'signal_strength': float(signal_data['signal_strength']),
                        'signal_description': signal_data['signal'],
                        'trend_direction': signal_data['trend_direction'],
                        'rsi': float(signal_data['rsi']),
                        'support_1': float(signal_data['support_1'].replace('$', '').replace(',', '')),
                        'support_2': float(signal_data['support_2'].replace('$', '').replace(',', '')),
                        'resistance_1': float(signal_data['resistance_1'].replace('$', '').replace(',', '')),
                        'resistance_2': float(signal_data['resistance_2'].replace('$', '').replace(',', '')),
                        'optimal_entry': float(signal_data['optimal_entry']),  # Added from signal_data
                        'optimal_exit': float(signal_data['optimal_exit']),    # Added from signal_data
                        'stop_loss': float(signal_data['stop_loss']),         # Added from signal_data
                        'dca_recommendation': signal_data['dca_recommendation'],
                        'historical_data': historical_prices,
                        'predictions': predictions,
                        'confidence_score': predictions.get('confidence_score', 0) if predictions else 0
                    }

                    logger.info(f"Successfully processed data for {token}")
                    return render_template('dashboard.html', **template_data)

                except Exception as e:
                    logger.error(f"Error processing data: {str(e)}")
                    raise ValueError(f"Error processing data: {str(e)}")
            else:
                logger.warning("No historical prices found in market data")
                raise ValueError("No historical price data available")

        except Exception as e:
            logger.error(f"Error processing search request: {str(e)}")
            error_message = f"Error analyzing token: {str(e)}"
            return render_template('dashboard.html', error=error_message, **DEFAULT_DATA)

    @app.template_filter('price_color')
    def price_color_filter(value):
        """Return CSS class based on price change value."""
        try:
            value = float(value)
            return 'text-green-500' if value >= 0 else 'text-red-500'
        except (ValueError, TypeError):
            return 'text-gray-500'

    return app

# Create and configure the application
app = create_app()

# Initialize database
with app.app_context():
    try:
        db.create_all()

        # Create default user if none exists
        if not User.query.first():
            default_user = User(
                username="default_user",
                email="default@example.com",
                points=0
            )
            db.session.add(default_user)
            db.session.commit()
            logger.info("Created default user")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")

if __name__ == '__main__':
    try:
        logger.info("Starting Flask server...")
        app.run(host='0.0.0.0', port=3000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")