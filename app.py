import os
from flask import Flask, render_template, request, jsonify
import asyncio
from services.technical_analysis import get_signal_analysis
from services.coingecko_service import get_token_price, get_token_market_data
import logging
from datetime import datetime, timedelta
from flask_talisman import Talisman
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import pandas as pd
from services.sentiment_service import calculate_sentiment_score
from services.sentiment_service import get_market_sentiment_data
from models import db, Quiz, Question, UserProgress, User
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS
CORS(app)

# Configure SQLAlchemy
if not os.environ.get('DATABASE_URL'):
    logger.error("DATABASE_URL environment variable is not set")
    sys.exit(1)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Security headers with relaxed CSP for Chart.js and D3.js
Talisman(app,
    content_security_policy={
        'default-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", 'cdn.jsdelivr.net', 'd3js.org', '*'],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", 'cdn.jsdelivr.net', 'd3js.org'],
        'style-src': ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net'],
        'img-src': ["'self'", 'data:', 'cdn.jsdelivr.net', '*'],
        'font-src': ["'self'", 'cdn.jsdelivr.net'],
        'connect-src': ["'self'", '*']
    },
    force_https=False
)

# Enable compression
Compress(app)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour"]
)

@app.route('/')
@limiter.exempt
def index():
    """Render the main dashboard."""
    try:
        logger.info("Rendering index page")
        return render_template('dashboard.html', error=None)
    except Exception as e:
        logger.exception("Error rendering index page")
        return render_template('dashboard.html', error=str(e))

@app.route('/search')
@limiter.limit("20 per minute")
def search():
    """Handle token search and analysis."""
    token = request.args.get('token', 'bitcoin').lower()
    try:
        logger.info(f"Processing search request for token: {token}")

        # Get market data and signal analysis using asyncio.run()
        price_data = asyncio.run(get_token_price(token))
        signal_data = asyncio.run(get_signal_analysis(token))
        market_data = asyncio.run(get_token_market_data(token))

        if not market_data or not price_data or not signal_data:
            raise ValueError("Unable to fetch complete market data for the token")

        logger.info(f"Retrieved data for {token}: Price=${price_data['usd']}, Signal strength={signal_data['signal_strength']}")

        # Calculate trend score and signal strength
        trend_score = min(100, max(0, float(signal_data['signal_strength'])))
        signal_strength = min(100, max(0, float(signal_data['signal_strength'])))

        # Calculate entry and exit prices
        current_price = float(price_data['usd'])
        support_1 = float(signal_data['support_1'].replace('$', '').replace(',', ''))
        support_2 = float(signal_data['support_2'].replace('$', '').replace(',', ''))
        resistance_1 = float(signal_data['resistance_1'].replace('$', '').replace(',', ''))
        resistance_2 = float(signal_data['resistance_2'].replace('$', '').replace(',', ''))

        optimal_entry = (current_price + support_1) / 2
        optimal_exit = (current_price + resistance_1) / 2
        stop_loss = support_2

        # Process historical data
        historical_prices = market_data.get('prices', [])
        if historical_prices:
            logger.info(f"Found {len(historical_prices)} historical price points")

            price_values = [price[1] for price in historical_prices]

            # Calculate price ranges for different periods
            prices_365d = price_values[-365:] if len(price_values) >= 365 else price_values
            prices_90d = price_values[-90:] if len(price_values) >= 90 else price_values
            prices_30d = price_values[-30:] if len(price_values) >= 30 else price_values
            prices_7d = price_values[-7:] if len(price_values) >= 7 else price_values

            # Prepare template data
            template_data = {
                'token_symbol': token.upper(),
                'price': current_price,
                'price_change': float(price_data['usd_24h_change']),
                'signal_strength': signal_strength,
                'signal_description': signal_data['signal'],
                'trend_score': trend_score,
                'trend_direction': signal_data['trend_direction'],
                'market_status': get_market_status(float(signal_data['rsi'])),
                'rsi': float(signal_data['rsi']),
                'support_1': support_1,
                'support_2': support_2,
                'resistance_1': resistance_1,
                'resistance_2': resistance_2,
                'optimal_entry': optimal_entry,
                'optimal_exit': optimal_exit,
                'stop_loss': stop_loss,
                'dca_recommendation': signal_data['dca_recommendation'],
                'historical_data': historical_prices,
                'yearly_high': max(prices_365d),
                'yearly_low': min(prices_365d),
                'ninety_day_high': max(prices_90d),
                'ninety_day_low': min(prices_90d),
                'thirty_day_high': max(prices_30d),
                'thirty_day_low': min(prices_30d),
                'seven_day_high': max(prices_7d),
                'seven_day_low': min(prices_7d),
                'chart_data': {
                    'labels': [price[0] for price in historical_prices],
                    'prices': [price[1] for price in historical_prices],
                    'support_levels': [float(support_1), float(support_2)],
                    'resistance_levels': [float(resistance_1), float(resistance_2)]
                }
            }

            # Calculate sentiment
            try:
                volume_change = market_data.get('total_volume_change_24h', 0)
                sentiment_score, sentiment_emoji, sentiment_description = calculate_sentiment_score(
                    price_change=float(price_data['usd_24h_change']),
                    volume_change=volume_change,
                    rsi=float(signal_data['rsi']),
                    current_price=current_price,
                    support_1=support_1,
                    resistance_1=resistance_1
                )
                logger.info(f"Sentiment analysis: Score={sentiment_score}, Emoji={sentiment_emoji}")
            except Exception as e:
                logger.error(f"Error calculating sentiment: {str(e)}")
                sentiment_score, sentiment_emoji, sentiment_description = 50.0, "⚖️", "Neutral"

            template_data.update({
                'sentiment_score': sentiment_score,
                'sentiment_emoji': sentiment_emoji,
                'sentiment_description': sentiment_description,
            })

            return render_template('dashboard.html', **template_data)
        else:
            raise ValueError("No historical price data available")

    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        return render_template('dashboard.html', error=str(e), **DEFAULT_DATA)

@app.template_filter('price_color')
def price_color_filter(value):
    """Return CSS class based on price change value."""
    try:
        value = float(value)
        return 'text-green-500' if value >= 0 else 'text-red-500'
    except (ValueError, TypeError):
        return 'text-gray-500'

def get_market_status(rsi):
    """Determine market status based on RSI."""
    if rsi >= 70:
        return "Overbought 🔴"
    elif rsi <= 30:
        return "Oversold 🟢"
    else:
        return "Neutral ⚖️"

@app.route('/api/market_sentiment')
@limiter.limit("30 per minute")
def market_sentiment():
    """Get market sentiment data for top cryptocurrencies."""
    try:
        logger.info("Fetching market sentiment data")
        sentiment_data = asyncio.run(get_market_sentiment_data())
        logger.info(f"Successfully fetched sentiment data for {len(sentiment_data)} tokens")
        return jsonify(sentiment_data)
    except Exception as e:
        logger.exception(f"Error fetching market sentiment: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Initialize database
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.exception("Error creating database tables")
        sys.exit(1)

if __name__ == '__main__':
    try:
        logger.info("Starting Flask server...")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=False
        )
    except Exception as e:
        logger.exception(f"Failed to start server: {str(e)}")
        sys.exit(1)

# Default template data
DEFAULT_DATA = {
    'token_symbol': 'Enter a token',
    'price': 0.0,
    'price_change': 0.0,
    'signal_strength': 0,
    'signal_description': 'Enter a token to analyze',
    'trend_score': 50,
    'trend_direction': 'Neutral ⚖️',
    'market_status': 'Neutral ⚖️',
    'rsi': 50,
    'support_1': 0.0,
    'support_2': 0.0,
    'resistance_1': 0.0,
    'resistance_2': 0.0,
    'optimal_entry': 0.0,
    'optimal_exit': 0.0,
    'stop_loss': 0.0,
    'dca_recommendation': 'Enter a token to get DCA recommendations',
    'historical_data': [],
    'seven_day_high': 0.0,
    'seven_day_low': 0.0,
    'thirty_day_high': 0.0,
    'thirty_day_low': 0.0,
    'ninety_day_high': 0.0,
    'ninety_day_low': 0.0,
    'yearly_high': 0.0,
    'yearly_low': 0.0,
    'chart_data': {
        'labels': [],
        'prices': [],
        'support_levels': [0, 0],
        'resistance_levels': [0, 0]
    },
    'sentiment_score': 50.0,
    'sentiment_emoji': "⚖️",
    'sentiment_description': "Neutral",
}