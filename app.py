import logging
import sys
import os

# Configure logging with full tracebacks
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

try:
    logger.info("Importing Flask...")
    from flask import Flask, render_template, request, jsonify
    from services.crypto_api import CryptoAPIService
    logger.info("Flask imported successfully")
except Exception as e:
    logger.critical(f"Failed to import Flask: {str(e)}", exc_info=True)
    sys.exit(1)

try:
    logger.info("Creating Flask app...")
    app = Flask(__name__)
    crypto_service = CryptoAPIService()

    @app.route('/')
    def index():
        return render_template('dashboard.html')

    @app.route('/api/market-data/<symbol>')
    def get_market_data(symbol):
        try:
            data = crypto_service.get_market_data(symbol.upper())
            logger.info(f"Market data for {symbol}: {data}")
            return jsonify(data)
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            return jsonify({"error": str(e)}), 500

except Exception as e:
    logger.critical(f"Failed to create Flask application: {str(e)}", exc_info=True)
    sys.exit(1)

if __name__ == '__main__':
    try:
        port = int(os.environ.get("PORT", 5000))  # Default to port 5000
        logger.info(f"Starting Flask server on port {port}...")
        # Start without debug mode and with minimal configuration
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.critical(f"Application startup failed: {str(e)}", exc_info=True)
        sys.exit(1)