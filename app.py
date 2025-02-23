import os
import logging
import socket
from flask import Flask, render_template, send_from_directory, jsonify
from services.crypto_analysis import CryptoAnalysisService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, 
               static_folder='static',
               static_url_path='/static'
              )
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['DEBUG'] = True

    try:
        logger.info("Initializing CryptoAnalysisService...")
        crypto_service = CryptoAnalysisService()
        logger.info("CryptoAnalysisService initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize CryptoAnalysisService: {str(e)}", exc_info=True)
        raise

    @app.route('/')
    def index():
        try:
            logger.debug("Rendering index page")
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering index page: {str(e)}", exc_info=True)
            return render_template('error.html', error=str(e)), 500

    @app.route('/dashboard')
    def dashboard():
        try:
            # Get basic market data
            logger.info("Fetching market data...")
            market_data = {
                'current_price': 0.0,
                'price_change_24h': 0.0,
                'market_cap': 0,
                'volume': 0
            }

            market_summary = crypto_service.get_market_summary()
            if market_summary:
                market_data.update({
                    'current_price': market_summary.get('current_price', 0.0),
                    'price_change_24h': market_summary.get('price_change_24h', 0.0),
                    'market_cap': market_summary.get('market_cap', 0),
                    'volume': market_summary.get('volume', 0)
                })
            else:
                logger.warning("Failed to fetch market data, using defaults")

            # Get historical data for the chart
            historical_data = crypto_service.get_historical_data()
            if not historical_data:
                logger.warning("Failed to fetch historical data")
                historical_data = []

            return render_template('dashboard.html',
                               market_data=market_data,
                               chart_data=historical_data.reset_index().to_dict('records') if not isinstance(historical_data, list) else [])

        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}")
            return render_template('error.html', error=str(e)), 500

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        try:
            logger.debug(f"Serving static file: {filename}")
            return send_from_directory(app.static_folder, filename)
        except Exception as e:
            logger.error(f"Error serving static file {filename}: {str(e)}", exc_info=True)
            return render_template('error.html', error=f"File not found: {filename}"), 404

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', error="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html', error="Internal server error"), 500

    return app

if __name__ == '__main__':
    try:
        # Ensure required directories exist
        os.makedirs('static/assets', exist_ok=True)

        # Get local IP address for logging
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"Local IP address: {local_ip}")

        # Create and configure the Flask app
        app = create_app()

        # Start server
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Flask server on port {port}")
        logger.info(f"Server will be accessible at http://{local_ip}:{port}")

        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            threaded=True
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise