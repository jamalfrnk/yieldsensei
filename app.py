import os
import logging
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize database
db = SQLAlchemy()

def create_app():
    """Application factory function."""
    try:
        logger.info("Starting application creation process")
        app = Flask(__name__)

        # Basic configuration
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        # Database configuration if URL is provided
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url
            db.init_app(app)
            with app.app_context():
                db.create_all()
                logger.info("Database initialized")

        @app.route('/')
        def index():
            try:
                # Default values for the dashboard
                technical_indicators = {
                    'rsi': {'value': 50.0, 'trend': 'Neutral', 'strength': 0.5},
                    'macd': {'signal': 'Neutral', 'crossover': 'None', 'trend_strength': 0.5}
                }

                price_levels = {
                    'support_1': 100.0,
                    'support_2': 95.0,
                    'resistance_1': 110.0,
                    'resistance_2': 115.0
                }

                trading_levels = {
                    'optimal_entry': 105.0,
                    'optimal_exit': 115.0,
                    'stop_loss': 95.0
                }

                price_ranges = {
                    'day': {'high': 110.0, 'low': 90.0},
                    'week': {'high': 115.0, 'low': 85.0},
                    'month': {'high': 120.0, 'low': 80.0},
                    'quarter': {'high': 125.0, 'low': 75.0},
                    'year': {'high': 130.0, 'low': 70.0}
                }

                ml_predictions = {
                    'next_day': {
                        'rf_prediction': 100.0,
                        'prophet_prediction': 100.0,
                        'combined_prediction': 100.0,
                        'upper_bound': 105.0,
                        'lower_bound': 95.0
                    }
                }

                dca_recommendation = (
                    "💡 Default DCA Strategy:\n"
                    "• Split your investment into 4-5 portions\n"
                    "• Invest 20% now at current levels\n"
                    "• Space remaining portions over 2-3 weeks\n"
                    "• Set stop-loss at strong support levels\n"
                    "• Consider increasing position size on dips"
                )

                context = {
                    'token_symbol': 'Enter a token',
                    'price': 100.0,
                    'price_change': 0.0,
                    'signal_strength': 50.0,
                    'signal_description': "Enter a token to view signal analysis",
                    'technical_indicators': technical_indicators,
                    'trend_direction': 'Neutral ⚖️',
                    'signal': 'Neutral',
                    'price_ranges': price_ranges,
                    'ml_predictions': ml_predictions,
                    'confidence_score': 50.0,
                    'price_levels': price_levels,
                    'trading_levels': trading_levels,
                    'dca_recommendation': dca_recommendation,
                    'fibonacci_levels': None
                }

                return render_template('dashboard.html', **context)
            except Exception as e:
                logger.error(f"Error rendering index: {str(e)}", exc_info=True)
                return render_template('error.html', error=str(e)), 500

        @app.route('/test')
        def test():
            return "Test endpoint working!"

        logger.info("Application creation completed")
        return app

    except Exception as e:
        logger.critical(f"Failed to create application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        logger.info("Creating application instance")
        app = create_app()
        # ALWAYS use port 5000 as required by Replit
        logger.info("Starting Flask server on port 5000")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise