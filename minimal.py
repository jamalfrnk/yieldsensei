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
    # Use global crypto_service instead of initializing a new one
    global crypto_service
    
    # Map common symbols to CoinGecko IDs
    symbol_map = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'SOL': 'solana',
        'ADA': 'cardano',
        'DOT': 'polkadot',
        'DOGE': 'dogecoin',
        'XRP': 'ripple',
        'AVAX': 'avalanche-2',
        'MATIC': 'matic-network'
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
        logger.info(f"Fetched market data for {coin_id}: {market_data['current_price']}")
    except Exception as e:
        logger.error(f"Market data error: {str(e)}")
        error_messages.append("Market data temporarily unavailable")

    # Fetch sentiment data
    try:
        sentiment_data = crypto_service.get_market_sentiment(coin_id)
        if sentiment_data:
            logger.info(f"Sentiment analysis for {coin_id}: {sentiment_data['label']}")
        else:
            # Create fallback sentiment if none available
            sentiment_data = {
                'score': 0.5,
                'label': 'Neutral ⚖️',
                'factors': ['Market showing mixed signals', 'Technical indicators inconclusive']
            }
    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        error_messages.append("Sentiment analysis temporarily unavailable")
        # Create fallback sentiment
        sentiment_data = {
            'score': 0.5,
            'label': 'Neutral ⚖️',
            'factors': ['Market showing mixed signals', 'Technical indicators inconclusive']
        }

    # Fetch historical data
    try:
        historical_data = crypto_service.get_historical_data(coin_id)
        if historical_data is not None and not historical_data.empty:
            logger.info(f"Fetched {len(historical_data)} historical data points for {coin_id}")
        else:
            logger.warning(f"No historical data available for {coin_id}")
    except Exception as e:
        logger.error(f"Historical data error: {str(e)}")
        error_messages.append("Historical data temporarily unavailable")

    # Calculate extended price ranges with real data where available
    try:
        # Get historical data for different time periods if available
        df_week = crypto_service.get_historical_data(coin_id, days=7)
        df_month = crypto_service.get_historical_data(coin_id, days=30)
        df_quarter = crypto_service.get_historical_data(coin_id, days=90)
        df_year = crypto_service.get_historical_data(coin_id, days=365)
        
        price_ranges = {
            'day': {
                'high': market_data.get('high_24h', 0),
                'low': market_data.get('low_24h', 0)
            },
            'week': {
                'high': float(df_week['price'].max()) if df_week is not None and not df_week.empty else market_data.get('high_24h', 0),
                'low': float(df_week['price'].min()) if df_week is not None and not df_week.empty else market_data.get('low_24h', 0)
            },
            'month': {
                'high': float(df_month['price'].max()) if df_month is not None and not df_month.empty else market_data.get('high_24h', 0),
                'low': float(df_month['price'].min()) if df_month is not None and not df_month.empty else market_data.get('low_24h', 0)
            },
            'quarter': {
                'high': float(df_quarter['price'].max()) if df_quarter is not None and not df_quarter.empty else market_data.get('high_24h', 0),
                'low': float(df_quarter['price'].min()) if df_quarter is not None and not df_quarter.empty else market_data.get('low_24h', 0)
            },
            'year': {
                'high': float(df_year['price'].max()) if df_year is not None and not df_year.empty else market_data.get('high_24h', 0),
                'low': float(df_year['price'].min()) if df_year is not None and not df_year.empty else market_data.get('low_24h', 0)
            }
        }
    except Exception as e:
        logger.error(f"Error calculating price ranges: {str(e)}")
        # Fallback to basic price ranges
        price_ranges = {
            'day': {
                'high': market_data.get('high_24h', 0),
                'low': market_data.get('low_24h', 0)
            },
            'week': {
                'high': market_data.get('high_24h', 0) * 1.05,
                'low': market_data.get('low_24h', 0) * 0.95
            },
            'month': {
                'high': market_data.get('high_24h', 0) * 1.15,
                'low': market_data.get('low_24h', 0) * 0.85
            },
            'quarter': {
                'high': market_data.get('high_24h', 0) * 1.25,
                'low': market_data.get('low_24h', 0) * 0.75
            },
            'year': {
                'high': market_data.get('high_24h', 0) * 1.5,
                'low': market_data.get('low_24h', 0) * 0.5
            }
        }

    # Parse the ISO date string to datetime object with fallback
    try:
        last_updated = datetime.fromisoformat(market_data.get('last_updated').replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        last_updated = datetime.now()

    # Get signal analysis for better DCA recommendations
    signal_data = None
    try:
        signal_data = crypto_service.get_signal_analysis(coin_id)
    except Exception as e:
        logger.error(f"Signal analysis error: {str(e)}")

    # Generate DCA recommendations with entry/exit points based on technical analysis
    current_price = market_data.get('current_price', 0)
    
    # Use signal data for better recommendations if available
    if signal_data and 'price_levels' in signal_data:
        support_1 = signal_data['price_levels'].get('support_1', current_price * 0.95)
        support_2 = signal_data['price_levels'].get('support_2', current_price * 0.90)
        resistance_1 = signal_data['price_levels'].get('resistance_1', current_price * 1.10)
        resistance_2 = signal_data['price_levels'].get('resistance_2', current_price * 1.20)
        
        # Risk level based on signal strength
        signal_strength = abs(signal_data.get('signal_strength', 0))
        if signal_strength > 70:
            risk_level = "High Risk 🔴"
            risk_explanation = "Strong market momentum detected. Consider smaller position sizes."
        elif signal_strength > 30:
            risk_level = "Medium Risk 🟡"
            risk_explanation = "Moderate market conditions. Standard position sizing recommended."
        else:
            risk_level = "Low Risk 🟢"
            risk_explanation = "Stable market conditions. Optimal for DCA strategy."
            
        # Dynamic DCA strategy based on risk level
        if risk_level == "High Risk 🔴":
            schedule = "Weekly small purchases spread across 6-8 weeks"
            allocations = ['20%', '30%', '50%']
        elif risk_level == "Medium Risk 🟡":
            schedule = "Bi-weekly purchases over 4-6 weeks"
            allocations = ['30%', '40%', '30%']
        else:
            schedule = "Monthly purchases spread across 3-4 months"
            allocations = ['40%', '30%', '30%']
    else:
        # Default values if signal analysis is not available
        support_1 = current_price * 0.95
        support_2 = current_price * 0.90
        resistance_1 = current_price * 1.15
        resistance_2 = current_price * 1.30
        risk_level = "Medium Risk 🟡"
        risk_explanation = "Market showing moderate volatility. Use staged entries."
        schedule = "Bi-weekly purchases over 4-6 weeks"
        allocations = ['30%', '40%', '30%']
        
    # Build DCA recommendations object
    dca_recommendations = {
        'entry_points': [
            {
                'price': current_price * 0.98,  # 2% below current price
                'allocation': allocations[0]
            },
            {
                'price': support_1,  # First support level
                'allocation': allocations[1]
            },
            {
                'price': support_2,  # Second support level
                'allocation': allocations[2]
            }
        ],
        'risk_level': risk_level,
        'risk_explanation': risk_explanation,
        'schedule': schedule,
        'exit_strategy': {
            'take_profit': [
                {'price': resistance_1, 'allocation': '30%'},  # First resistance
                {'price': resistance_2, 'allocation': '40%'},  # Second resistance
                {'price': resistance_2 * 1.15, 'allocation': '30%'}  # Extended target
            ],
            'stop_loss': support_2 * 0.95,  # 5% below second support
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
        days_value = days_map.get(days, '1')

        df = crypto_service.get_historical_data(symbol.lower(), int(days_value))
        if df.empty:
            logger.warning(f"No price history data available for {symbol}")
            # Return sample data to avoid frontend errors
            return jsonify(generate_sample_price_data(int(days_value)))

        # Safely handle different DataFrame formats
        formatted_data = []
        
        # Check if we have a proper DataFrame with timestamp index
        if isinstance(df.index, pd.DatetimeIndex):
            # Reset index to convert timestamp from index to column
            df_reset = df.reset_index()
            # Extract timestamp and price columns
            for _, row in df_reset.iterrows():
                formatted_data.append({
                    'timestamp': row.iloc[0].isoformat() if hasattr(row.iloc[0], 'isoformat') else str(row.iloc[0]),
                    'price': float(row['price']) if 'price' in df else float(row.iloc[1])
                })
        else:
            # Handle case where index is not timestamp
            for idx, row in df.iterrows():
                # Ensure we have a timestamp column or use current time with offset
                timestamp = row.get('timestamp', datetime.now() - timedelta(days=int(days_value) - idx/len(df)*int(days_value)))
                price = row.get('price', 0)
                formatted_data.append({
                    'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                    'price': float(price)
                })
        
        return jsonify(formatted_data)
    except Exception as e:
        logger.error(f"Error fetching price history: {str(e)}")
        # Return sample data to avoid frontend errors
        return jsonify(generate_sample_price_data(int(days_map.get(days, '1'))))

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