import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from config import get_config, Config
import logging

# Initialize database
db = SQLAlchemy()

def create_app():
    """Application factory function."""
    try:
        # Initialize logging
        Config.init_logging()

        # Get logger after configuration
        logger = logging.getLogger(__name__)
        logger.info("Starting application creation process")

        # Create Flask app
        app = Flask(__name__)

        # Load configuration
        config = get_config()
        app.config.from_object(config)

        # Initialize extensions
        if app.config['SQLALCHEMY_DATABASE_URI']:
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

                return render_template('dashboard.html',
                    token_symbol='Enter a token',
                    price=100.0,
                    price_change=0.0,
                    signal_strength=50.0,
                    signal_description="Enter a token to view signal analysis",
                    technical_indicators=technical_indicators,
                    trend_direction='Neutral ⚖️',
                    signal='Neutral',
                    price_levels=price_levels,
                    trading_levels=trading_levels,
                    dca_recommendation="Enter a token to view DCA strategy"
                )
            except Exception as e:
                logger.error(f"Error rendering index: {str(e)}", exc_info=True)
                return render_template('error.html', error=str(e)), 500

        @app.route('/test')
        def test():
            return "Test endpoint working!"

        logger.info("Application creation completed")
        return app

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"Failed to create application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        logger = logging.getLogger(__name__)
        app = create_app()
        # ALWAYS serve the app on port 5000
        logger.info("Starting Flask server on port 5000")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise