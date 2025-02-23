import os
import logging
import sys
from flask import Flask, render_template, send_from_directory, jsonify
import pandas as pd
import numpy as np
from services.crypto_analysis import CryptoAnalysisService
import socket

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to stdout for immediate feedback
        logging.FileHandler('yieldsensei.log')
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    try:
        # Initialize Flask app with explicit static folder configuration
        app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static'
        )

        # Configure Flask app
        app.config['SECRET_KEY'] = os.urandom(24)
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.config['DEBUG'] = True

        # Initialize services with error handling
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
                logger.debug("Attempting to fetch dashboard data...")
                historical_data = crypto_service.get_historical_data()
                if historical_data is None:
                    logger.error("Failed to fetch historical data")
                    raise Exception("Failed to fetch cryptocurrency data")

                market_summary = crypto_service.get_market_summary()
                if market_summary is None:
                    logger.error("Failed to fetch market summary")
                    raise Exception("Failed to fetch market data")

                logger.debug(f"Successfully fetched market data: {market_summary}")

                # Calculate price ranges
                current_price = historical_data['price'].iloc[-1]
                price_ranges = {
                    'day': {
                        'high': historical_data['price'].tail(24).max(),
                        'low': historical_data['price'].tail(24).min(),
                        'change': ((current_price - historical_data['price'].iloc[-2]) / historical_data['price'].iloc[-2]) * 100
                    },
                    'week': {
                        'high': historical_data['price'].tail(7 * 24).max(),
                        'low': historical_data['price'].tail(7 * 24).min(),
                        'change': ((current_price - historical_data['price'].iloc[-7]) / historical_data['price'].iloc[-7]) * 100
                    },
                    'month': {
                        'high': historical_data['price'].tail(30 * 24).max(),
                        'low': historical_data['price'].tail(30 * 24).min(),
                        'change': ((current_price - historical_data['price'].iloc[-30]) / historical_data['price'].iloc[-30]) * 100
                    }
                }

                support_1 = float(historical_data['support_1'].iloc[-1])
                support_2 = float(historical_data['support_2'].iloc[-1])
                resistance_1 = float(historical_data['resistance_1'].iloc[-1])
                resistance_2 = float(historical_data['resistance_2'].iloc[-1])

                # Get sentiment analysis
                try:
                    sentiment_data = crypto_service.get_market_sentiment()
                    logger.debug("Successfully fetched sentiment data")
                except Exception as e:
                    logger.warning(f"Failed to fetch sentiment data: {str(e)}")
                    sentiment_data = None

                # Get DCA recommendations
                try:
                    dca_recommendations = crypto_service.get_dca_recommendations()
                    logger.debug("Successfully fetched DCA recommendations")
                except Exception as e:
                    logger.warning(f"Failed to fetch DCA recommendations: {str(e)}")
                    dca_recommendations = None

                logger.debug("Preparing to render dashboard template")
                return render_template('dashboard.html',
                                    market_summary=market_summary,
                                    historical_data=historical_data.reset_index().to_dict('records'),
                                    price_ranges=price_ranges,
                                    support_1=support_1,
                                    support_2=support_2,
                                    resistance_1=resistance_1,
                                    resistance_2=resistance_2,
                                    sentiment_data=sentiment_data,
                                    dca_recommendations=dca_recommendations)
            except Exception as e:
                logger.error(f"Error rendering dashboard page: {str(e)}", exc_info=True)
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

    except Exception as e:
        logger.critical(f"Failed to create Flask application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        # Ensure required directories exist
        os.makedirs('static/assets', exist_ok=True)

        # Copy the image file to static/assets if it doesn't exist
        source_image = 'attached_assets/blackyieldsensei.webp'
        dest_image = 'static/assets/blackyieldsensei.webp'
        if os.path.exists(source_image) and not os.path.exists(dest_image):
            import shutil
            shutil.copy2(source_image, dest_image)
            logger.info(f"Copied {source_image} to {dest_image}")

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

        # Use threaded=True and specify host as 0.0.0.0 to ensure accessibility
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            threaded=True
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise