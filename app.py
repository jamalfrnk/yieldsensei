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
from models import db, Quiz, Question, UserProgress, User

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Default data for the dashboard
DEFAULT_DATA = {
    'token_symbol': 'Enter a token',
    'price': 0.0,
    'price_change': 0.0,
    'signal_strength': 0,
    'signal_description': 'Enter a token to analyze',
    'trend_direction': 'Neutral ⚖️',
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
    }
}

app = Flask(__name__)

# Enable CORS with proper configuration
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Security headers
Talisman(app,
    content_security_policy={
        'default-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", 'cdn.jsdelivr.net', '*'],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", 'cdn.jsdelivr.net'],
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
async def index():
    """Render the main dashboard."""
    logger.info("Rendering index page")
    return render_template('dashboard.html', **DEFAULT_DATA)

@app.route('/search')
@limiter.limit("20 per minute")
async def search():
    """Handle token search and analysis."""
    token = request.args.get('token', 'bitcoin').lower()
    try:
        logger.info(f"Processing search request for token: {token}")

        # Get market data and signal analysis
        price_data = await get_token_price(token)
        signal_data = await get_signal_analysis(token)
        market_data = await get_token_market_data(token)

        if not market_data or not price_data or not signal_data:
            raise ValueError("Unable to fetch complete market data for the token")

        logger.info(f"Retrieved data for {token}: Price=${price_data['usd']}, Signal strength={signal_data['signal_strength']}")

        # Calculate signal strength in 0-100 range
        signal_strength = min(100, max(0, float(signal_data['signal_strength'])))

        # Calculate entry and exit prices based on support and resistance levels
        current_price = float(price_data['usd'])
        support_1 = float(signal_data['support_1'].replace('$', '').replace(',', ''))
        support_2 = float(signal_data['support_2'].replace('$', '').replace(',', ''))
        resistance_1 = float(signal_data['resistance_1'].replace('$', '').replace(',', ''))
        resistance_2 = float(signal_data['resistance_2'].replace('$', '').replace(',', ''))

        # Calculate optimal entry and exit prices
        optimal_entry = (current_price + support_1) / 2
        optimal_exit = (current_price + resistance_1) / 2
        stop_loss = support_2

        # Extract historical price data
        historical_prices = []
        if 'prices' in market_data and market_data['prices']:
            historical_prices = market_data['prices']
            logger.info(f"Found {len(historical_prices)} historical price points")

            try:
                # Convert prices to a list of values only (excluding timestamps)
                price_values = [price[1] for price in historical_prices]

                # Calculate indices for different time periods
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
                    'trend_direction': signal_data['trend_direction'],
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

                logger.info(f"Successfully processed data for {token}")
                return render_template('dashboard.html', **template_data)

            except Exception as e:
                logger.error(f"Error processing historical data: {str(e)}")
                raise ValueError(f"Error processing historical data: {str(e)}")
        else:
            logger.warning("No historical prices found in market data")
            raise ValueError("No historical price data available")

    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        error_message = f"Error analyzing token: {str(e)}"
        return render_template('dashboard.html', error=error_message, **DEFAULT_DATA)

@app.template_filter('price_color')
def price_color_filter(value):
    """Return CSS class based on price change value."""
    try:
        value = float(value)
        return 'text-green-500' if value >= 0 else 'text-red-500'
    except (ValueError, TypeError):
        return 'text-gray-500'

# Initialize database
with app.app_context():
    db.create_all()

    # Create default user if none exists
    if not User.query.first():
        default_user = User(
            username="default_user",
            email="default@example.com",
            points=0
        )
        db.session.add(default_user)
        db.session.commit()

if __name__ == '__main__':
    try:
        logger.info("Starting Flask server...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")