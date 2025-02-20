import os
from flask import Flask, render_template, request, jsonify
from asgiref.wsgi import WsgiToAsgi
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
from models import db, Quiz, Question, UserProgress, User
import sys
from hypercorn.config import Config
from hypercorn.asyncio import serve

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

async def index():
    """Render the main dashboard."""
    try:
        logger.info("Rendering index page")
        return render_template('dashboard.html', **DEFAULT_DATA)
    except Exception as e:
        logger.exception("Error rendering index page")
        return render_template('dashboard.html', error=str(e), **DEFAULT_DATA)

async def search():
    """Handle token search and analysis."""
    token = request.args.get('token', 'bitcoin').lower()
    try:
        logger.info(f"Processing search request for token: {token}")

        # Create tasks for concurrent execution
        tasks = [
            get_token_price(token),
            get_signal_analysis(token),
            get_token_market_data(token)
        ]

        # Wait for all tasks to complete
        price_data, signal_data, market_data = await asyncio.gather(*tasks)

        if not all([market_data, price_data, signal_data]):
            raise ValueError("Unable to fetch complete market data for the token")

        logger.info(f"Retrieved data for {token}: Price=${price_data['usd']}, Signal strength={signal_data['signal_strength']}")

        # Process data and create response
        template_data = {
            'token_symbol': token.upper(),
            'price': float(price_data['usd']),
            'price_change': float(price_data['usd_24h_change']),
            'signal_strength': float(signal_data['signal_strength']),
            'signal_description': signal_data['signal'],
            'trend_score': float(signal_data['signal_strength']),
            'trend_direction': signal_data['trend_direction'],
            'market_status': get_market_status(float(signal_data['rsi'])),
            'rsi': float(signal_data['rsi']),
            'historical_data': market_data.get('prices', []),
            'chart_data': {
                'labels': [price[0] for price in market_data.get('prices', [])],
                'prices': [price[1] for price in market_data.get('prices', [])],
                'support_levels': [float(signal_data['support_1'].replace('$', '').replace(',', '')), 
                                 float(signal_data['support_2'].replace('$', '').replace(',', ''))],
                'resistance_levels': [float(signal_data['resistance_1'].replace('$', '').replace(',', '')), 
                                    float(signal_data['resistance_2'].replace('$', '').replace(',', ''))]
            }
        }

        return render_template('dashboard.html', **template_data)

    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        return render_template('dashboard.html', error=str(e), **DEFAULT_DATA)

# Update route declarations to use async views
app.route('/')(index)
app.route('/search')(search)


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
        logger.info("Starting Hypercorn server...")
        config = Config()
        config.bind = ["0.0.0.0:5000"]
        config.use_reloader = True
        config.workers = 1
        config.accesslog = "-"  # Log to stdout

        app = WsgiToAsgi(app)
        asyncio.run(serve(app, config))
    except Exception as e:
        logger.exception(f"Failed to start server: {str(e)}")
        sys.exit(1)