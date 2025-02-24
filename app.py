from flask import Flask, render_template, redirect, url_for
import logging
import sys
import os
from models import db
from services.coingecko_service import get_token_price, get_token_market_data
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    # Create Flask app
    app = Flask(__name__)

    # Log database configuration
    logger.info("Configuring database connection...")

    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    logger.info(f"Using database URL: {database_url.split('@')[1] if database_url else 'None'}")  # Log only the host part

    # Initialize extensions
    db.init_app(app)

    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    # Simple ping route for health check
    @app.route('/ping')
    def ping():
        return 'pong'

    # Main routes
    @app.route('/')
    def index():
        """Main dashboard view"""
        try:
            logger.info("Accessing dashboard route")

            # Create event loop for async calls
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            logger.info("Fetching market data for bitcoin")
            try:
                # Get market data for BTC by default
                market_data = loop.run_until_complete(get_token_market_data('bitcoin'))
                logger.info("Successfully retrieved market data")
            except Exception as e:
                logger.error(f"Error fetching market data: {e}")
                market_data = None
            finally:
                # Close the event loop
                loop.close()

            return render_template('dashboard.html', 
                                market_data={
                                    'current_price': market_data['high_24h'] if market_data else 0.0,
                                    'price_change_24h': market_data['price_change_percentage_24h'] if market_data else 0.0,
                                    'market_cap': market_data['market_cap'] if market_data else 0,
                                    'volume': market_data['total_volume'] if market_data else 0
                                })
        except Exception as e:
            logger.error(f"Error rendering dashboard: {e}", exc_info=True)
            return render_template('dashboard.html', 
                                market_data={
                                    'current_price': 0.0,
                                    'price_change_24h': 0.0,
                                    'market_cap': 0,
                                    'volume': 0
                                })

    @app.route('/docs')
    def documentation():
        return render_template('documentation.html')

    @app.route('/telegram')
    def telegram():
        return render_template('telegram.html')

    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)