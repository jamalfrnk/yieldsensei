import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required
from models import db, User
from datetime import datetime
import logging
from sqlalchemy import text
from flask_talisman import Talisman
from flask_compress import Compress
from waitress import serve

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

def create_app():
    """Application factory function."""
    logger.info("Starting application creation process")
    app = Flask(__name__)

    # Basic configuration
    logger.info("Setting up basic configuration")
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-change-in-production'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    # Configure database
    logger.info("Configuring database connection")
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        logger.info(f"Database URL configured: {database_url.split('@')[1] if '@' in database_url else 'configured'}")

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

    # Initialize login manager
    logger.info("Initializing login manager")
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Initialize production-ready middleware
    Compress(app)  # Enable compression

    # Configure Talisman for security headers
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        'img-src': ["'self'", "data:", "https://cdn.jsdelivr.net"],
        'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdn.jsdelivr.net"],
        'connect-src': ["'self'", "https://api.coingecko.com"]
    }
    Talisman(app, 
        force_https=False,  # Set to True in production
        strict_transport_security=True,
        session_cookie_secure=True,
        content_security_policy=csp
    )

    # Basic test route
    @app.route('/test')
    def test():
        logger.info("Test endpoint accessed")
        return jsonify({
            'status': 'ok',
            'message': 'Server is running',
            'timestamp': datetime.utcnow().isoformat()
        })

    # Health check endpoint
    @app.route('/health')
    def health_check():
        try:
            db.session.execute(text('SELECT 1'))
            logger.info("Health check passed")
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Basic dashboard route."""
        try:
            return render_template('dashboard.html', 
                token_symbol='Enter a token',
                price=0.0,
                price_change=0.0,
                trend_direction='Neutral ⚖️'
            )
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}")
            return render_template('error.html', error=str(e)), 500

    # Error handlers
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {str(error)}")
        return render_template('error.html', error="An internal error occurred. Please try again later."), 500

    @app.errorhandler(404)
    def not_found_error(error):
        logger.error(f"Page Not Found: {request.url}")
        return render_template('error.html', error="Page not found"), 404

    logger.info("Application creation completed successfully")
    return app

if __name__ == '__main__':
    try:
        logger.info("Creating application instance")
        app = create_app()
        port = int(os.environ.get('PORT', 3000))  # Changed default port to 3000
        logger.info(f"Starting production server on port {port}")
        serve(app, host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
        raise