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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security headers
Talisman(app, 
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net'],
        'style-src': ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net'],
        'img-src': ["'self'", 'data:', 'cdn.jsdelivr.net'],
        'font-src': ["'self'", 'cdn.jsdelivr.net']
    },
    force_https=False  # Disable HTTPS for local development
)

# Enable compression
Compress(app)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour"]
)

# Register template filters
@app.template_filter('price_color')
def price_color_filter(value):
    """Return CSS class based on price change value."""
    try:
        value = float(value)
        return 'text-green-500' if value >= 0 else 'text-red-500'
    except (ValueError, TypeError):
        return 'text-gray-500'

@app.route('/')
@limiter.exempt
async def index():
    """Render the main dashboard."""
    default_data = {
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
        'dca_recommendation': 'Enter a token to get DCA recommendations',
        'chart_data': {
            'labels': [],
            'datasets': []
        }
    }
    return render_template('dashboard.html', **default_data)

@app.route('/search')
@limiter.limit("20 per minute")
async def search():
    """Handle token search and analysis."""
    token = request.args.get('token', 'bitcoin').lower()
    try:
        # Get market data
        price_data = await get_token_price(token)
        signal_data = await get_signal_analysis(token)

        # Calculate trend score (0-100)
        trend_score = min(100, max(0, float(signal_data['signal_strength'])))

        template_data = {
            'price': float(price_data['usd']),
            'price_change': float(price_data['usd_24h_change']),
            'signal_strength': float(signal_data['signal_strength']),
            'signal_description': signal_data['signal'],
            'trend_score': trend_score,
            'trend_direction': signal_data['trend_direction'],
            'market_status': get_market_status(float(signal_data['rsi'])),
            'rsi': float(signal_data['rsi']),
            'support_1': float(signal_data['support_1'].replace('$', '').replace(',', '')),
            'support_2': float(signal_data['support_2'].replace('$', '').replace(',', '')),
            'resistance_1': float(signal_data['resistance_1'].replace('$', '').replace(',', '')),
            'resistance_2': float(signal_data['resistance_2'].replace('$', '').replace(',', '')),
            'dca_recommendation': signal_data['dca_recommendation']
        }

        return render_template('dashboard.html', **template_data)
    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        return render_template('dashboard.html', error=str(e), **default_data)

def get_market_status(rsi):
    """Determine market status based on RSI."""
    if rsi >= 70:
        return "Overbought 🔴"
    elif rsi <= 30:
        return "Oversold 🟢"
    else:
        return "Neutral ⚖️"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)