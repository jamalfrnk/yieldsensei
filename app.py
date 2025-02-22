import os
import logging
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

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

@login_manager.user_loader
def load_user(user_id):
    from models import User  # Import here to avoid circular import
    return User.query.get(int(user_id))

def create_app():
    """Application factory function."""
    try:
        logger.info("Starting application creation process")
        app = Flask(__name__)

        # Basic configuration
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        # Database configuration
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url

        # Initialize extensions with app
        db.init_app(app)
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'

        # Create database tables
        with app.app_context():
            db.create_all()
            logger.info("Database initialized")

        # Register blueprints
        from auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint)

        @app.route('/')
        def index():
            try:
                # Default values for the dashboard
                context = {
                    'token_symbol': 'Enter a token',
                    'price': 100.0,
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
                        'day': {'high': 110.0, 'low': 90.0},
                        'week': {'high': 115.0, 'low': 85.0},
                        'month': {'high': 120.0, 'low': 80.0},
                        'quarter': {'high': 125.0, 'low': 75.0},
                        'year': {'high': 130.0, 'low': 70.0}
                    },
                    'ml_predictions': None,
                    'confidence_score': 50.0,
                    'price_levels': {
                        'support_1': 95.0,
                        'support_2': 90.0,
                        'resistance_1': 105.0,
                        'resistance_2': 110.0
                    },
                    'trading_levels': {
                        'optimal_entry': 100.0,
                        'optimal_exit': 105.0,
                        'stop_loss': 95.0
                    },
                    'dca_recommendation': "Enter a token to view DCA recommendations",
                    'fibonacci_levels': None
                }
                return render_template('dashboard.html', **context)
            except Exception as e:
                logger.error(f"Error rendering index: {str(e)}", exc_info=True)
                return render_template('error.html', error=str(e)), 500

        logger.info("Application creation completed")
        return app

    except Exception as e:
        logger.critical(f"Failed to create application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        app = create_app()
        # Always serve on port 5000 for Replit
        logger.info("Starting Flask server on port 5000")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise