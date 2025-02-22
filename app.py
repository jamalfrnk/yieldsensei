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
from models import db, User

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
    'optimal_entry': 0.0,
    'optimal_exit': 0.0,
    'stop_loss': 0.0,
    'dca_recommendation': 'Enter a token to get DCA recommendations',
    'historical_data': [],
    'predictions': None,
    'confidence_score': 0,
    'price_ranges': {
        'day': {'high': 0.0, 'low': 0.0},
        'week': {'high': 0.0, 'low': 0.0},
        'month': {'high': 0.0, 'low': 0.0},
        'quarter': {'high': 0.0, 'low': 0.0},
        'year': {'high': 0.0, 'low': 0.0}
    }
}

def create_app():
    app = Flask(__name__)

    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # Enable CORS
    CORS(app)

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
        default_limits=["150 per minute"]
    )

    @app.route('/')
    @limiter.exempt
    def index():
        """Render the landing page."""
        return render_template('index.html')

    @app.route('/dashboard')
    @limiter.exempt
    async def dashboard():
        """Render the main dashboard."""
        return render_template('dashboard.html', **DEFAULT_DATA)

    @app.route('/search')
    @limiter.limit("200 per minute")
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

            # Calculate template data
            template_data = {
                'token_symbol': token.upper(),
                'price': float(price_data['usd']),
                'price_change': float(price_data.get('usd_24h_change', 0)),
                'signal_strength': float(signal_data['signal_strength']),
                'signal_description': signal_data['signal'],
                'trend_direction': signal_data['trend_direction'],
                'rsi': float(signal_data['rsi']),
                'support_1': float(signal_data['support_1'].replace('$', '').replace(',', '')),
                'support_2': float(signal_data['support_2'].replace('$', '').replace(',', '')),
                'resistance_1': float(signal_data['resistance_1'].replace('$', '').replace(',', '')),
                'resistance_2': float(signal_data['resistance_2'].replace('$', '').replace(',', '')),
                'optimal_entry': float(signal_data['optimal_entry']),
                'optimal_exit': float(signal_data['optimal_exit']),
                'stop_loss': float(signal_data['stop_loss']),
                'dca_recommendation': signal_data['dca_recommendation']
            }

            logger.info(f"Successfully processed data for {token}")
            return render_template('dashboard.html', **template_data)

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
        port = int(os.environ.get('PORT', 3000))
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")