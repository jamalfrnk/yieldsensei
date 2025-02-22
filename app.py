import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
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
from auth import auth
from services.token_service import get_token_data # Added import statement


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
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_secret_key'),  # Set a default for development
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

    # Environment-specific settings
    is_development = os.environ.get('ENVIRONMENT', 'production').lower() == 'development'
    logger.info(f"Running in {'development' if is_development else 'production'} mode")

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
                db.session.execute(text('SELECT 1'))
                db.session.commit()
                logger.info("Database initialized and connected successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    else:
        logger.error("DATABASE_URL environment variable is not set")
        raise RuntimeError("DATABASE_URL environment variable must be set")

    # Initialize rate limiter with environment-specific settings
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per day", "100 per hour"] if not is_development else [],
        storage_uri=os.environ.get("REDIS_URL", "memory://"),
        strategy="fixed-window-elastic-expiry"
    )

    # Initialize login manager
    logger.info("Initializing login manager")
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Set the login view
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    logger.info("Registering blueprints")
    app.register_blueprint(auth, url_prefix='/auth')  # Register auth blueprint with prefix

    # Initialize production-ready middleware
    Compress(app)

    # Configure Talisman with environment-specific settings
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

    if is_development:
        logger.info("Development mode: Relaxing security settings")
        csp['connect-src'].append("*")
        Talisman(app,
            force_https=False,
            strict_transport_security=False,
            session_cookie_secure=False,
            content_security_policy=csp
        )
    else:
        logger.info("Production mode: Enforcing strict security settings")
        Talisman(app,
            force_https=True,
            strict_transport_security=True,
            session_cookie_secure=True,
            content_security_policy=csp,
            content_security_policy_report_only=False
        )

    # Main routes
    @app.route('/')
    def index():
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering index page: {str(e)}")
            return render_template('error.html', error="An error occurred loading the page"), 500

    @app.route('/dashboard')
    @login_required
    @limiter.limit("100 per hour")
    def dashboard():
        try:
            # Initialize default technical indicators structure
            technical_indicators = {
                'rsi': {
                    'value': 50.0,
                    'trend': 'Neutral',
                    'strength': 0.5
                },
                'macd': {
                    'signal': 'Neutral',
                    'crossover': 'None',
                    'trend_strength': 0.5
                }
            }

            # Default trading levels
            trading_levels = {
                'optimal_entry': 0.0,
                'stop_loss': 0.0,
                'optimal_exit': 0.0
            }

            # Default price levels
            price_levels = {
                'support_1': 0.0,
                'support_2': 0.0,
                'resistance_1': 0.0,
                'resistance_2': 0.0
            }

            return render_template('dashboard.html',
                token_symbol='Enter a token',
                price=0.0,
                price_change=0.0,
                rsi=50.0,
                signal_strength=50.0,
                signal_description="Enter a token to view analysis",
                technical_indicators=technical_indicators,
                trend_direction='Neutral ⚖️',
                signal='Neutral',
                fibonacci_levels=None,
                price_ranges={
                    'day': {'high': 0.0, 'low': 0.0},
                    'week': {'high': 0.0, 'low': 0.0},
                    'month': {'high': 0.0, 'low': 0.0},
                    'quarter': {'high': 0.0, 'low': 0.0},
                    'year': {'high': 0.0, 'low': 0.0}
                },
                ml_predictions={
                    'next_day': {
                        'rf_prediction': 0.0,
                        'prophet_prediction': 0.0,
                        'combined_prediction': 0.0,
                        'upper_bound': 0.0,
                        'lower_bound': 0.0
                    }
                },
                confidence_score=50.0,
                historical_data=[],
                price_levels=price_levels,
                trading_levels=trading_levels,
                # Add individual price level variables for the chart
                support_1=price_levels['support_1'],
                support_2=price_levels['support_2'],
                resistance_1=price_levels['resistance_1'],
                resistance_2=price_levels['resistance_2']
            )
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}")
            return render_template('error.html', error=str(e)), 500

    @app.route('/search')
    @login_required
    @limiter.limit("100 per hour")
    async def search():
        try:
            token = request.args.get('token', '').lower()
            if not token:
                return redirect(url_for('dashboard'))

            # Fetch real-time token data
            token_data = get_token_data(token)
            if not token_data:
                logger.error(f"Could not fetch data for token: {token}")
                return render_template('error.html', 
                    error=f"Could not fetch data for token: {token.upper()}"), 404

            try:
                from services.technical_analysis import get_signal_analysis
                # Get technical analysis data with proper await
                analysis_data = await get_signal_analysis(token)

                # Structure technical indicators data
                technical_indicators = {
                    'rsi': {
                        'value': analysis_data['rsi'],
                        'trend': 'Bullish' if analysis_data['rsi'] > 50 else 'Bearish',
                        'strength': abs(analysis_data['rsi'] - 50) / 50
                    },
                    'macd': {
                        'signal': analysis_data.get('macd_signal', 'Neutral'),
                        'crossover': analysis_data.get('macd_crossover', 'None'),
                        'trend_strength': analysis_data.get('macd_trend_strength', 0.5)
                    }
                }

                return render_template('dashboard.html',
                    token_symbol=token_data["token_symbol"],
                    price=token_data["price"],
                    price_change=token_data["price_change"],
                    signal_strength=analysis_data['signal_strength'],
                    signal_description=analysis_data['signal'],
                    technical_indicators=technical_indicators,
                    trend_direction=analysis_data['trend_direction'],
                    fibonacci_levels=analysis_data.get('fibonacci_levels'),
                    price_ranges=token_data["price_ranges"],
                    ml_predictions=analysis_data.get('ml_predictions', {
                        'next_day': {
                            'rf_prediction': token_data["price"] * 1.01,
                            'prophet_prediction': token_data["price"] * 1.02,
                            'combined_prediction': token_data["price"] * 1.015,
                            'upper_bound': token_data["price"] * 1.05,
                            'lower_bound': token_data["price"] * 0.95
                        }
                    }),
                    confidence_score=analysis_data.get('confidence_score', 50.0),
                    historical_data=token_data.get("historical_data", []),
                    price_levels=analysis_data.get('price_levels', {
                        'support_1': token_data["price"] * 0.95,
                        'support_2': token_data["price"] * 0.90,
                        'resistance_1': token_data["price"] * 1.05,
                        'resistance_2': token_data["price"] * 1.10
                    }),
                    trading_levels=analysis_data.get('trading_levels', {
                        'optimal_entry': token_data["price"] * 0.98,
                        'stop_loss': token_data["price"] * 0.93,
                        'optimal_exit': token_data["price"] * 1.07
                    }),
                    dca_recommendation=analysis_data.get('dca_recommendation', 
                        f"Consider entering {token.upper()} at ${token_data['price']*0.98:,.2f}")
                )
            except Exception as e:
                logger.error(f"Error in technical analysis: {str(e)}")
                return render_template('error.html', error=str(e)), 500

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
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
        logger.info(f"Starting server on port {port}")
        if os.environ.get('ENVIRONMENT', 'production').lower() == 'development':
            app.run(host='0.0.0.0', port=port, debug=True)
        else:
            logger.info("Starting production server")
            serve(app, host='0.0.0.0', port=port, threads=4)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
        raise