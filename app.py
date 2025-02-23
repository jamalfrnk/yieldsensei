import os
import logging
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    """Application factory function."""
    app = Flask(__name__)

    try:
        logger.info("Starting application creation process")

        # Basic configuration
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        # Database configuration
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        logger.info("Database URL configured successfully")

        # Initialize extensions with app
        db.init_app(app)
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'

        @login_manager.user_loader
        def load_user(user_id):
            try:
                from models import User
                return User.query.get(int(user_id))
            except Exception as e:
                logger.error(f"Error loading user: {str(e)}")
                return None

        # Create database tables
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")

        # Register blueprints
        from auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint)
        logger.info("Auth blueprint registered")

        @app.route('/')
        def index():
            try:
                logger.info("Rendering index page")
                return render_template('index.html')
            except Exception as e:
                logger.error(f"Error rendering index: {str(e)}", exc_info=True)
                return render_template('error.html', error=str(e)), 500

        @app.route('/dashboard')
        def dashboard():
            try:
                logger.info("Rendering dashboard page")
                context = {
                    'token_symbol': 'Enter a token',
                    'price': 0.0,
                    'price_change': 0.0,
                    'signal_strength': 50.0,
                    'signal_description': "Enter a token to view signal analysis",
                    'technical_indicators': {
                        'rsi': {'value': 50.0, 'trend': 'Neutral', 'strength': 0.5},
                        'macd': {'signal': 'Neutral', 'crossover': 'None', 'trend_strength': 0.5}
                    },
                    'trend_direction': 'Neutral ⚖️',
                    'signal': 'Neutral',
                    'price_ranges': {
                        'day': {'high': 0.0, 'low': 0.0},
                        'week': {'high': 0.0, 'low': 0.0},
                        'month': {'high': 0.0, 'low': 0.0},
                        'quarter': {'high': 0.0, 'low': 0.0},
                        'year': {'high': 0.0, 'low': 0.0}
                    }
                }
                return render_template('dashboard.html', **context)
            except Exception as e:
                logger.error(f"Error rendering dashboard: {str(e)}", exc_info=True)
                return render_template('error.html', error=str(e)), 500

        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('error.html', error="Page not found"), 404

        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            return render_template('error.html', error="Internal server error"), 500

        logger.info("Application creation completed successfully")
        return app

    except Exception as e:
        logger.critical(f"Failed to create application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        app = create_app()
        logger.info("Starting Flask server on 0.0.0.0:5000")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise