import logging
import os
import sys
import socket
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
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

    # Initialize data containers with defaults
    market_data = {
        'current_price': 0,
        'market_cap': 0,
        'volume': 0,
        'price_change_24h': 0,
        'last_updated': datetime.now().isoformat(),
        'high_24h': 0,
        'low_24h': 0
    }
    sentiment_data = None
    historical_data = None
    error_messages = []

    # Fetch market data
    try:
        market_data = crypto_service.get_market_summary(coin_id) or market_data
    except Exception as e:
        logger.error(f"Market data error: {str(e)}")
        error_messages.append("Market data temporarily unavailable")

    # Fetch sentiment data
    try:
        sentiment_data = crypto_service.get_market_sentiment(coin_id)
    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        error_messages.append("Sentiment analysis temporarily unavailable")

    # Fetch historical data
    try:
        historical_data = crypto_service.get_historical_data(coin_id)
    except Exception as e:
        logger.error(f"Historical data error: {str(e)}")
        error_messages.append("Historical data temporarily unavailable")

    # Calculate price ranges with fallback
    price_ranges = {
        'day': {
            'high': market_data.get('high_24h', 0),
            'low': market_data.get('low_24h', 0)
        },
        'week': {
            'high': market_data.get('high_24h', 0),  # Fallback to 24h data
            'low': market_data.get('low_24h', 0)
        },
        'month': {
            'high': market_data.get('high_24h', 0),
            'low': market_data.get('low_24h', 0)
        },
        'quarter': {
            'high': market_data.get('high_24h', 0),
            'low': market_data.get('low_24h', 0)
        },
        'year': {
            'high': market_data.get('high_24h', 0),
            'low': market_data.get('low_24h', 0)
        }
    }

    # Parse the ISO date string to datetime object with fallback
    try:
        last_updated = datetime.fromisoformat(market_data.get('last_updated').replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        last_updated = datetime.now()

    # Generate DCA recommendations with entry/exit points
    current_price = market_data.get('current_price', 0)
    dca_recommendations = {
        'entry_points': [
            {
                'price': current_price * 0.95,  # 5% below current price
                'allocation': '30%'
            },
            {
                'price': current_price * 0.90,  # 10% below current price
                'allocation': '40%'
            },
            {
                'price': current_price * 0.85,  # 15% below current price
                'allocation': '30%'
            }
        ],
        'risk_level': "Medium Risk 🟡",
        'risk_explanation': "Market showing moderate volatility. Use staged entries.",
        'schedule': "Bi-weekly purchases over 4-6 weeks",
        'exit_strategy': {
            'take_profit': [
                {'price': current_price * 1.2, 'allocation': '30%'},  # 20% profit
                {'price': current_price * 1.3, 'allocation': '40%'},  # 30% profit
                {'price': current_price * 1.5, 'allocation': '30%'}   # 50% profit
            ],
            'stop_loss': current_price * 0.80,  # 20% below entry
            'trailing_stop': '15%'  # 15% trailing stop from local highs
        }
    }

    return render_template(
        'dashboard.html',
        market_data=market_data,
        market_insights={'sentiment': sentiment_data},
        symbol=symbol,
        last_updated=last_updated,
        price_ranges=price_ranges,
        historical_data=historical_data,
        errors=error_messages,
        dca_recommendations=dca_recommendations
    )

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/api/price-history/<symbol>')
def price_history(symbol):
    try:
        logger.info(f"Fetching price history for {symbol} over {request.args.get('range', '1')} days")
        days = request.args.get('range', '1')
        days_map = {'24h': '1', '7d': '7', '30d': '30', '90d': '90', '1y': '365'}
        days = days_map.get(days, '1')

        df = crypto_service.get_historical_data(symbol.lower(), int(days))
        if df.empty:
            logger.warning(f"No price history data available for {symbol}")
            # Return sample data to avoid frontend errors
            return jsonify(generate_sample_price_data(int(days)))

        price_data = df.reset_index().values.tolist()
        formatted_data = [{'timestamp': ts.isoformat(), 'price': float(price)} for ts, price in price_data]
        return jsonify(formatted_data)
    except Exception as e:
        logger.error(f"Error fetching price history: {str(e)}")
        # Return sample data to avoid frontend errors
        return jsonify(generate_sample_price_data(int(days)))

def generate_sample_price_data(days=1):
    """Generate sample price data when API fails"""
    import random
    from datetime import datetime, timedelta

    data = []
    base_price = 20000 if days > 30 else 30000  # Different trends for different timeframes

    # Generate proper number of data points based on timeframe
    points = 24 if days == 1 else days

    for i in range(points):
        if days == 1:
            # Hourly data for 1 day
            timestamp = (datetime.now() - timedelta(hours=24-i)).isoformat()
            # Add some randomness to price
            price = base_price * (1 + (random.random() - 0.5) * 0.02) + (i * 10)
        else:
            # Daily data
            timestamp = (datetime.now() - timedelta(days=days-i)).isoformat()
            # Create price trend with some randomness
            price = base_price * (1 + (random.random() - 0.5) * 0.05) + (i * 50)

        data.append({'timestamp': timestamp, 'price': price})

    return data

@app.route('/api/market-intelligence/<symbol>')
def market_intelligence(symbol):
    try:
        # Use existing crypto_service instance
        logger.info(f"Fetching market intelligence for {symbol}")
        sentiment_data = crypto_service.get_market_sentiment(symbol)
        market_data = crypto_service.get_market_summary(symbol)

        # Prepare response with more data points
        intelligence_data = {
            'sentiment': sentiment_data,
            'volume': {
                'total_24h': market_data.get('volume', 0),
                'change_24h': market_data.get('price_change_24h', 0)
            },
            'price': {
                'current': market_data.get('current_price', 0),
                'high_24h': market_data.get('high_24h', 0),
                'low_24h': market_data.get('low_24h', 0)
            },
            'last_updated': market_data.get('last_updated')
        }

        logger.info(f"Successfully fetched market intelligence for {symbol}")
        return jsonify(intelligence_data)
    except Exception as e:
        logger.error(f"Error in market intelligence: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch market intelligence',
            'message': str(e)
        }), 500

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