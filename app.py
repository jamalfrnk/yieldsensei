import logging
from flask import Flask, render_template, request
from flask_cors import CORS
from datetime import datetime, timezone
from waitress import serve
from services.crypto_api import CryptoAPIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize API service
crypto_api = CryptoAPIService()

def create_app():
    """Create and configure the Flask application"""
    try:
        logger.info("Creating Flask application...")
        app = Flask(__name__)
        CORS(app)

        @app.route('/health')
        def health_check():
            logger.info("Health check endpoint called")
            return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}, 200

        @app.route('/')
        def index():
            try:
                return render_template('index.html')
            except Exception as e:
                logger.error(f"Error rendering index page: {str(e)}")
                return f"Error: {str(e)}", 500

        @app.route('/dashboard')
        def dashboard():
            try:
                symbol = request.args.get('symbol', 'BTC').upper()
                logger.info(f"Fetching market data for {symbol}")

                market_data = crypto_api.get_market_data(symbol)
                logger.info(f"Retrieved market data for {symbol}")

                return render_template('dashboard.html', 
                    market_data=market_data,
                    last_updated=datetime.now(timezone.utc)
                )
            except Exception as e:
                logger.error(f"Dashboard error: {str(e)}", exc_info=True)
                return f"Error: {str(e)}", 500

        logger.info("Flask application created successfully")
        return app

    except Exception as e:
        logger.critical(f"Failed to create Flask application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        logger.info("Creating and configuring application...")
        app = create_app()

        logger.info("Starting Waitress server on port 5000...")
        serve(app, host='0.0.0.0', port=5000)

    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise