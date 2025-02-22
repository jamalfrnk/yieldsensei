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
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('yieldsensei.log')
    ]
)
logger = logging.getLogger(__name__)

# Set default environment variables if not present
os.environ['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'development')
os.environ['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

logger.info(f"Starting application in {os.environ['FLASK_ENV']} mode")

def create_app():
    app = Flask(__name__)

    # Determine environment
    is_production = os.environ.get('FLASK_ENV') == 'production'
    logger.info(f"Application environment: {'production' if is_production else 'development'}")

    try:
        # Initialize basic Flask configuration first
        app.config.update(
            ENV='production' if is_production else 'development',
            DEBUG=not is_production
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

        # Initialize database after configuration
        logger.info("Initializing database")
        db.init_app(app)
        logger.info("Database initialized successfully")

        # Production-specific configuration
        if is_production:
            logger.info("Applying production-specific configuration")
            app.config.update(
                SESSION_COOKIE_SECURE=True,
                SESSION_COOKIE_HTTPONLY=True,
                PERMANENT_SESSION_LIFETIME=timedelta(days=1)
            )

            # Configure CORS for production
            CORS(app, resources={
                r"/*": {
                    "origins": ["https://yieldsensei.ai", "https://www.yieldsensei.ai"],
                    "methods": ["GET", "POST", "OPTIONS"],
                    "allow_headers": ["Content-Type", "Authorization"]
                }
            })

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
            logger.info("Adding production CSP rules")
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

        # Try to configure rate limiting without blocking startup
        try:
            redis_url = os.environ.get('REDIS_URL')
            logger.info("Attempting to configure rate limiting")
            if redis_url:
                limiter = Limiter(
                    app=app,
                    key_func=get_remote_address,
                    default_limits=["200 per hour", "50 per minute"],
                    storage_uri=redis_url
                )
                logger.info("Rate limiting configured successfully")
            else:
                logger.warning("No Redis URL configured, skipping rate limiting")
        except Exception as e:
            logger.error(f"Failed to configure rate limiting: {str(e)}")
            logger.info("Continuing without rate limiting")

        @app.before_request
        def before_request():
            if is_production and not request.is_secure:
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)

        @app.route('/')
        def index():
            return render_template('index.html')

        @app.route('/dashboard')
        async def dashboard():
            return render_template('dashboard.html', **DEFAULT_DATA)

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

    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise

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

if __name__ == '__main__':
    try:
        logger.info("Creating application instance")
        app = create_app()

        port = int(os.environ.get('PORT', 3000))
        host = '0.0.0.0'

        logger.info(f"Starting server on {host}:{port}")
        if os.environ.get('FLASK_ENV') == 'production':
            logger.info("Using production server (waitress)")
            serve(app, host=host, port=port, threads=4)
        else:
            logger.info("Using development server (Flask)")
            app.run(host=host, port=port, debug=True)

    except Exception as e:
        logger.error(f"Critical error during server startup: {str(e)}", exc_info=True)
        raise