import os
import logging
import socket
import pandas as pd
from flask import Flask, render_template, send_from_directory, jsonify
from services.crypto_analysis import CryptoAnalysisService
from services.openai_service import get_crypto_news_sync
from services.sentiment_service import calculate_sentiment_score
from datetime import datetime, timezone

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

    # Initialize CryptoAnalysisService with error handling
    try:
        logger.info("Initializing CryptoAnalysisService...")
        crypto_service = CryptoAnalysisService()
        logger.info("CryptoAnalysisService initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize CryptoAnalysisService: {str(e)}", exc_info=True)
        crypto_service = None  # Allow app to start even if service fails

    @app.route('/test')
    def test():
        """Test route to verify server functionality"""
        try:
            logger.info("Test route accessed")
            return jsonify({"status": "ok", "message": "Server is running"})
        except Exception as e:
            logger.error(f"Error in test route: {str(e)}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500

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
            # Verify crypto_service is available
            if not crypto_service:
                logger.error("CryptoAnalysisService not initialized")
                return render_template('error.html', error="Service temporarily unavailable"), 503

            # Get basic market data
            logger.info("Fetching market data...")
            market_data = {
                'current_price': 0.0,
                'price_change_24h': 0.0,
                'market_cap': 0,
                'volume': 0
            }

            try:
                market_summary = crypto_service.get_market_summary()
                if market_summary:
                    market_data.update(market_summary)
            except Exception as e:
                logger.error(f"Error fetching market data: {str(e)}")

            # Get historical data for the chart
            chart_data = []
            try:
                historical_data = crypto_service.get_historical_data()
                if isinstance(historical_data, pd.DataFrame) and not historical_data.empty:
                    chart_data = historical_data.reset_index().to_dict('records')
                else:
                    logger.warning("Historical data is not available")
            except Exception as e:
                logger.error(f"Error fetching historical data: {str(e)}")

            # Get AI-generated market insights
            market_insights = None
            last_updated = None
            try:
                logger.info("Fetching AI market insights...")
                crypto_news = get_crypto_news_sync()  # Using synchronous version

                sentiment_score, sentiment_emoji, sentiment_description = calculate_sentiment_score(
                    price_change=market_data['price_change_24h'],
                    volume_change=0,
                    rsi=50,
                    current_price=market_data['current_price'],
                    support_1=market_data['current_price'] * 0.95,
                    resistance_1=market_data['current_price'] * 1.05
                )

                market_insights = {
                    'summary': crypto_news,
                    'sentiment': {
                        'score': sentiment_score,
                        'label': f"{sentiment_emoji} {sentiment_description}",
                    },
                    'factors': [
                        "Price momentum analysis",
                        "Volume analysis",
                        "Technical indicators"
                    ],
                    'outlook': "Market analysis and predictions will be updated every hour."
                }
                last_updated = datetime.now(timezone.utc)
            except Exception as e:
                logger.error(f"Error generating market insights: {str(e)}")

            return render_template('dashboard.html',
                               market_data=market_data,
                               chart_data=chart_data,
                               market_insights=market_insights,
                               last_updated=last_updated)

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
        # Get local IP address for logging
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"Local IP address: {local_ip}")

        # Create and configure the Flask app
        app = create_app()

        # Always use port 5000 as required by Replit
        port = 5000
        logger.info(f"Starting Flask server on port {port}")
        logger.info(f"Server will be accessible at http://{local_ip}:{port}")

        app.run(
            host='0.0.0.0',
            port=port,
            debug=True
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise