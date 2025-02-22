import os
from flask import Flask, render_template, request, jsonify, redirect
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
from waitress import serve

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='yieldsensei.log'
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

    # Determine environment
    is_production = os.environ.get('FLASK_ENV') == 'production'

    # Base configuration
    app.config['ENV'] = 'production' if is_production else 'development'
    app.config['DEBUG'] = not is_production

    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Production-specific configuration
    if is_production:
        app.config['SERVER_NAME'] = 'yieldsensei.ai'
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

    # Initialize extensions
    db.init_app(app)

    # Configure CORS
    if is_production:
        CORS(app, resources={
            r"/*": {
                "origins": ["https://yieldsensei.ai", "https://www.yieldsensei.ai"],
                "methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        })
    else:
        CORS(app)

    # Security headers
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com"],
        'img-src': ["'self'", "data:", "https://cdn.jsdelivr.net"],
        'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdn.jsdelivr.net"],
        'connect-src': ["'self'", "https://api.coingecko.com"]
    }

    if is_production:
        # Add production-specific CSP rules
        for directive in csp:
            csp[directive].extend([
                "https://*.yieldsensei.ai",
                "https://www.yieldsensei.ai"
            ])

    Talisman(app,
        force_https=is_production,
        strict_transport_security=is_production,
        session_cookie_secure=is_production,
        content_security_policy=csp
    )

    # Enable compression
    Compress(app)

    # Configure rate limiting
    redis_url = os.environ.get('REDIS_URL')
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri=redis_url if redis_url else None
    )

    @app.before_request
    def before_request():
        if is_production and not request.is_secure:
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

    @app.route('/')
    @limiter.exempt
    def index():
        return render_template('index.html')

    @app.route('/dashboard')
    @limiter.exempt
    async def dashboard():
        return render_template('dashboard.html', **DEFAULT_DATA)

    @app.route('/search')
    @limiter.limit("200 per hour")
    async def search():
        token = request.args.get('token', 'bitcoin').lower()
        try:
            logger.info(f"Processing search request for token: {token}")
            price_data = await get_token_price(token)
            signal_data = await get_signal_analysis(token)
            market_data = await get_token_market_data(token)

            if not market_data or not price_data or not signal_data:
                raise ValueError("Unable to fetch complete market data for the token")

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

            return render_template('dashboard.html', **template_data)

        except Exception as e:
            logger.error(f"Error processing search request: {str(e)}")
            error_message = f"Error analyzing token: {str(e)}"
            return render_template('dashboard.html', error=error_message, **DEFAULT_DATA)

    @app.template_filter('price_color')
    def price_color_filter(value):
        try:
            value = float(value)
            return 'text-green-500' if value >= 0 else 'text-red-500'
        except (ValueError, TypeError):
            return 'text-gray-500'

    return app

# Create and configure the application
app = create_app()

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 3000))
        if os.environ.get('FLASK_ENV') == 'production':
            logger.info("Starting production server...")
            serve(app, host='0.0.0.0', port=port, threads=4)
        else:
            logger.info("Starting development server...")
            app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")