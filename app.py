import os
import logging
import socket
import time
from typing import Optional, Dict, Any
import pandas as pd
from flask import Flask, render_template, send_from_directory, jsonify
from services.crypto_analysis import CryptoAnalysisService
from services.openai_service import init_openai_service, get_crypto_news_sync
from services.sentiment_service import calculate_sentiment_score
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_services() -> Optional[CryptoAnalysisService]:
    """Initialize application services with proper error handling and retries"""
    crypto_service = None
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            # Initialize OpenAI service first
            logger.info(f"Initializing OpenAI service (attempt {attempt + 1}/{max_retries})...")
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                logger.warning("OPENAI_API_KEY not found in environment variables")
            init_openai_service(openai_api_key)

            # Initialize CryptoAnalysis service
            logger.info(f"Initializing CryptoAnalysisService (attempt {attempt + 1}/{max_retries})...")
            crypto_service = CryptoAnalysisService()

            # Test service connectivity
            if crypto_service.get_market_summary():
                logger.info("Services initialized and tested successfully")
                return crypto_service

        except ImportError as e:
            logger.error(f"Failed to import required module: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Service initialization error (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue

    logger.error("Failed to initialize services after all retries")
    return None

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, 
               static_folder='static',
               static_url_path='/static')

    # Basic Flask configuration
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['DEBUG'] = True

    # Initialize services
    crypto_service = init_services()

    @app.route('/test')
    def test():
        """Test route to verify server functionality"""
        return jsonify({"status": "ok", "message": "Server is running"})

    @app.route('/')
    def index():
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering index page: {str(e)}")
            return render_template('error.html', error=str(e)), 500

    @app.route('/dashboard')
    def dashboard():
        try:
            logger.info("Accessing dashboard route")
            if not crypto_service:
                logger.error("Crypto service not initialized")
                return render_template('error.html', error="Service temporarily unavailable"), 503

            # Basic market data structure with defaults
            market_data = {
                'current_price': 0.0,
                'price_change_24h': 0.0,
                'market_cap': 0,
                'volume': 0,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }

            chart_data = []
            market_insights = None
            last_updated = None

            # Only try to get market data if service is available
            if crypto_service:
                try:
                    market_summary = crypto_service.get_market_summary()
                    if market_summary:
                        market_data.update(market_summary)

                    historical_data = crypto_service.get_historical_data()
                    if isinstance(historical_data, pd.DataFrame) and not historical_data.empty:
                        chart_data = historical_data.reset_index().to_dict('records')
                except Exception as e:
                    logger.error(f"Error fetching market data: {str(e)}")

            # Generate market insights
            try:
                crypto_news = get_crypto_news_sync()
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
                        'score': sentiment_score / 100.0,  # Convert to 0-1 range
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
            return send_from_directory(app.static_folder, filename)
        except Exception as e:
            logger.error(f"Error serving static file {filename}: {str(e)}")
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
        app = create_app()
        port = int(os.getenv('PORT', 3000))

        # Test if port is available
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('0.0.0.0', port))
        sock.close()

        if result == 0:
            logger.warning(f"Port {port} is in use, trying next available port")
            port += 1

        logger.info(f"Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise