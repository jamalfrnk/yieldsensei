import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required
from models import db, User
from datetime import datetime, timedelta
import logging
from sqlalchemy import text, create_engine
from sqlalchemy.pool import QueuePool
from flask_talisman import Talisman
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from waitress import serve

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('yieldsensei.log')
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """Application factory function."""
    logger.info("Starting application creation process")
    app = Flask(__name__)

    # Basic configuration
    logger.info("Setting up basic configuration")
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=1),
        SQLALCHEMY_ENGINE_OPTIONS={
            'pool_size': 10,
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'pool_timeout': 30
        }
    )

    if not app.config['SECRET_KEY']:
        raise RuntimeError("SECRET_KEY environment variable must be set")

    # Configure database
    logger.info("Configuring database connection")
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        logger.info("Database URL configured successfully")

        # Initialize database with error handling
        try:
            logger.info("Initializing database")
            db.init_app(app)
            with app.app_context():
                db.create_all()
                # Verify database connection
                db.session.execute(text('SELECT 1'))
                db.session.commit()
                logger.info("Database initialized and connected successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    else:
        logger.error("DATABASE_URL environment variable is not set")
        raise RuntimeError("DATABASE_URL environment variable must be set")

    # Initialize rate limiter with more lenient defaults for production
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["2000 per day", "200 per hour"],  # More lenient limits
        storage_uri=os.environ.get("REDIS_URL", "memory://"),
        strategy="fixed-window-elastic-expiry"
    )

    # Exempt static files and common routes from rate limiting
    @limiter.request_filter
    def exempt_static_and_common():
        return request.path.startswith('/static/') or request.path == '/'

    # Initialize login manager
    logger.info("Initializing login manager")
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.session_protection = 'strong'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Initialize production-ready middleware
    Compress(app)

    # Configure Talisman with updated CSP
    csp = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            "https://cdn.jsdelivr.net",
            "https://cdn.tailwindcss.com",
            "https://api.coingecko.com"
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
            "https://cdn.jsdelivr.net",
            "https://cdn.tailwindcss.com"
        ],
        'img-src': ["'self'", "data:", "https://*"],
        'font-src': [
            "'self'",
            "https://fonts.gstatic.com",
            "https://cdn.jsdelivr.net"
        ],
        'connect-src': [
            "'self'",
            "https://api.coingecko.com",
            "wss://api.coingecko.com"
        ]
    }

    Talisman(app,
        force_https=True,
        strict_transport_security=True,
        session_cookie_secure=True,
        content_security_policy=csp,
        content_security_policy_report_only=False
    )

    # Main routes with adjusted rate limits
    @app.route('/')
    def index():
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering index page: {str(e)}")
            return render_template('error.html', error="An error occurred loading the page"), 500

    @app.route('/dashboard')
    @login_required
    @limiter.limit("300 per hour")  # Increased limit for dashboard
    def dashboard():
        try:
            return render_template('dashboard.html', 
                token_symbol='Enter a token',
                price=0.0,
                price_change=0.0,
                signal_strength=50.0,
                signal_description="Neutral",
                rsi=50.0,
                trend_direction='Neutral ⚖️'
            )
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}")
            return render_template('error.html', error=str(e)), 500

    # Error handlers
    @app.errorhandler(429)
    def ratelimit_handler(e):
        logger.warning(f"Rate limit exceeded: {str(e)}")
        return render_template('error.html', 
            error="Rate limit exceeded. Please try again in a few minutes."), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {str(error)}")
        return render_template('error.html', 
            error="An internal error occurred. Please try again later."), 500

    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"Page Not Found: {request.url}")
        return render_template('error.html', error="Page not found"), 404

    logger.info("Application creation completed successfully")
    return app

if __name__ == '__main__':
    try:
        logger.info("Creating application instance")
        app = create_app()
        port = int(os.environ.get('PORT', 3000))
        logger.info(f"Starting production server on port {port}")
        serve(app, host='0.0.0.0', port=port, threads=4)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
        raise