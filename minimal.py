import logging
import os
import sys
import socket
from datetime import datetime
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from services.crypto_analysis import CryptoAnalysisService
from services.ml_prediction_service import MLPredictionService
from services.coingecko_service import get_token_price
from services.technical_analysis import get_signal_analysis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('flask_app.log')
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

crypto_service = CryptoAnalysisService()
ml_service = MLPredictionService()

@app.route('/')
def index():
    logger.info("Handling request for index page")
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    try:
        # Initialize the crypto service
        crypto_service = CryptoAnalysisService()
        
        # Map common symbols to CoinGecko IDs
        symbol_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana'
        }
        
        # Get default market data for Bitcoin
        symbol = request.args.get('symbol', 'BTC')
        coin_id = symbol_map.get(symbol, symbol.lower())
        
        market_data = crypto_service.get_market_summary(coin_id)
        sentiment_data = crypto_service.get_market_sentiment(coin_id)
        
        # Parse the ISO date string to datetime object
        last_updated = datetime.fromisoformat(market_data.get('last_updated').replace('Z', '+00:00'))
        
        return render_template(
            'dashboard.html',
            market_data=market_data,
            market_insights={'sentiment': sentiment_data},
            symbol=symbol,
            last_updated=last_updated
        )
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return render_template(
            'error.html',
            error_message="Failed to load market data. Please try again later."
        )

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/api/market-intelligence/<symbol>')
def market_intelligence(symbol):
    try:
        crypto_service = CryptoAnalysisService()
        sentiment_data = crypto_service.get_market_sentiment(symbol)
        market_data = crypto_service.get_market_summary(symbol)
        
        return jsonify({
            'sentiment': sentiment_data,
            'volume': {
                'total_24h': market_data['volume'],
                'change_24h': market_data['price_change_24h']
            }
        })
    except Exception as e:
        logger.error(f"Error in market intelligence: {str(e)}")
        return jsonify({'error': 'Failed to fetch market intelligence'}), 500

if __name__ == '__main__':
    try:
        # Less intrusive port check: Log a warning instead of exiting
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('0.0.0.0', 3000))
        if result == 0:
            logger.warning("Port 3000 may already be in use.  Continuing anyway.")
        sock.close()

        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")

        logger.info("Starting minimal Flask server...")
        app.run(
            host='0.0.0.0',
            port=3000,
            debug=True
        )
    except Exception as e:
        logger.error(f"Failed to start Flask server: {str(e)}", exc_info=True)
        raise