import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import asyncio
import threading
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
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
from auth import auth as auth_blueprint

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('yieldsensei.log')
    ]
)
logger = logging.getLogger(__name__)

# Thread-local storage for event loops
thread_local = threading.local()

def get_event_loop():
    """Get or create an event loop for the current thread."""
    if not hasattr(thread_local, "loop"):
        thread_local.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_local.loop)
    return thread_local.loop

def run_async(coro):
    """Utility function to run async code in sync context with proper error handling."""
    try:
        loop = get_event_loop()
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Error in async operation: {str(e)}", exc_info=True)
        raise

def create_app():
    """Application factory function."""
    app = Flask(__name__)

    # Set development mode
    app.config.update(
        ENV='development',
        DEBUG=True,
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    )

    # Initialize core extensions
    logger.info("Initializing core extensions")
    CORS(app)
    Compress(app)
    logger.info("Core extensions initialized successfully")

    # Initialize database configuration
    logger.info("Configuring database connection")
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable is not set")
        raise RuntimeError("DATABASE_URL environment variable must be set")

    # Convert heroku postgres URL if necessary
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # Configure SQLAlchemy
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    # Initialize database
    logger.info("Initializing database")
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    logger.info("Database initialized successfully")

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_blueprint)

    # Basic security headers
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com"],
        'img-src': ["'self'", "data:", "https://cdn.jsdelivr.net"],
        'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdn.jsdelivr.net"],
        'connect-src': ["'self'", "https://api.coingecko.com"]
    }

    Talisman(app,
        force_https=False,  # Disabled for development
        strict_transport_security=False,
        session_cookie_secure=False,
        content_security_policy=csp
    )

    # Routes
    @app.route('/health')
    def health_check():
        return 'OK', 200

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard route handler with price analysis."""
        try:
            # Get token from query params if provided
            token = request.args.get('token', None)
            data = DEFAULT_DATA.copy()

            if token:
                try:
                    logger.info(f"Fetching data for token: {token}")

                    # Fetch token price and market data
                    price_data = run_async(get_token_price(token))
                    logger.info(f"Price data received for {token}")

                    market_data = run_async(get_token_market_data(token))
                    logger.info(f"Market data received for {token}")

                    if price_data and market_data:
                        # Update price ranges with actual data
                        data.update({
                            'token_symbol': token.upper(),
                            'price': price_data.get('usd', 0.0),
                            'price_change': price_data.get('usd_24h_change', 0.0),
                            'price_ranges': {
                                'day': {
                                    'high': market_data.get('high_24h', 0.0),
                                    'low': market_data.get('low_24h', 0.0)
                                },
                                'week': {
                                    'high': market_data.get('high_7d', 0.0),
                                    'low': market_data.get('low_7d', 0.0)
                                },
                                'month': {
                                    'high': market_data.get('high_30d', 0.0),
                                    'low': market_data.get('low_30d', 0.0)
                                },
                                'quarter': {
                                    'high': market_data.get('high_90d', 0.0),
                                    'low': market_data.get('low_90d', 0.0)
                                },
                                'year': {
                                    'high': market_data.get('high_365d', 0.0),
                                    'low': market_data.get('low_365d', 0.0)
                                }
                            }
                        })
                        logger.info(f"Price ranges updated for {token}")

                        # Get additional analysis data
                        signal_data = run_async(get_signal_analysis(token))
                        if signal_data:
                            data.update({
                                'signal_strength': signal_data.get('signal_strength', 0),
                                'signal_description': signal_data.get('signal', 'Neutral'),
                                'trend_direction': signal_data.get('trend_direction', 'Neutral ⚖️'),
                                'rsi': signal_data.get('rsi', 50),
                            })
                            logger.info(f"Signal analysis completed for {token}")

                        # Get ML predictions if available
                        try:
                            predictions = run_async(ml_service.get_predictions(token))
                            if predictions:
                                data['predictions'] = predictions
                                data['confidence_score'] = predictions.get('confidence', 0)
                                logger.info(f"ML predictions received for {token}")
                        except Exception as e:
                            logger.error(f"Failed to get predictions for {token}: {str(e)}")

                except Exception as e:
                    error_msg = f"Error fetching data for {token}: {str(e)}"
                    logger.error(error_msg)
                    return render_template('dashboard.html', error=error_msg, **DEFAULT_DATA)

            return render_template('dashboard.html', **data)

        except Exception as e:
            error_msg = f"Dashboard error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return render_template('dashboard.html', error=error_msg, **DEFAULT_DATA)

    # Add error handlers
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {str(error)}")
        return render_template('error.html', error=str(error)), 500

    @app.errorhandler(404)
    def not_found_error(error):
        logger.error(f"Page Not Found: {request.url}")
        return render_template('error.html', error="Page not found"), 404

    logger.info("Application configured successfully")
    return app

# Default data structure
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

if __name__ == '__main__':
    try:
        logger.info("Creating application instance")
        app = create_app()

        port = int(os.environ.get('PORT', 3000))
        host = '0.0.0.0'

        logger.info(f"Starting development server on {host}:{port}")
        app.run(host=host, port=port)

    except Exception as e:
        logger.error(f"Critical error during server startup: {str(e)}", exc_info=True)
        raise