import os
import logging
import socket
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
    """Initialize application services with proper error handling"""
    crypto_service = None
    try:
        # Initialize OpenAI service first
        logger.info("Initializing OpenAI service...")
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        init_openai_service(openai_api_key)

        # Initialize CryptoAnalysis service
        logger.info("Initializing CryptoAnalysisService...")
        crypto_service = CryptoAnalysisService()
        logger.info("CryptoAnalysisService initialized successfully")

        return crypto_service
    except ImportError as e:
        logger.error(f"Failed to import required module: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Service initialization error: {str(e)}")
        return None  # Allow app to start with degraded functionality

def create_app():
    """Create and configure the Flask application"""
    try:
        app = Flask(__name__, 
                   static_folder='static',
                   static_url_path='/static'
                  )

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
                # Basic market data structure
                market_data = {
                    'current_price': 0.0,
                    'price_change_24h': 0.0,
                    'market_cap': 0,
                    'volume': 0
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
    except Exception as e:
        logger.critical(f"Failed to create Flask app: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        # Get local IP address for logging
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"Local IP address: {local_ip}")

        # Create the Flask app
        app = create_app()

        # Always serve the app on port 5000
        port = 3000
        logger.info(f"Starting Flask server on port {port}")
        logger.info(f"Server will be accessible at http://{local_ip}:{port}")

        app.run(
            host='0.0.0.0',  # Listen on all available interfaces
            port=port,
            debug=True
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise