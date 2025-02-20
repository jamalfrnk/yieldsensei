from flask import Flask, render_template, request, jsonify, redirect, url_for
import asyncio
from services.technical_analysis import get_signal_analysis
from services.coingecko_service import get_token_price, get_token_market_data
import logging
from datetime import datetime, timedelta
from asgiref.wsgi import WsgiToAsgi
from flask_talisman import Talisman
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from models import User
import os
import socket

# Configure logging with more detail for development
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Changed to DEBUG for more verbose output
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a random secret key for development

# Security headers with development settings
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

# Configure rate limiting with development limits
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "200 per hour"]  # More lenient limits for development
)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Development configuration
app.config.update(
    ENV='development',
    DEBUG=True,
    TESTING=True,  # Enable testing mode for development
    SEND_FILE_MAX_AGE_DEFAULT=0,  # Disable cache for development
    JSON_SORT_KEYS=False,
    PREFERRED_URL_SCHEME='http',
    SERVER_NAME=None  # Allow all host headers
)

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get(int(user_id))

# Authentication routes
@app.route('/login')
def login():
    """Development login route that automatically logs in as dev user."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    user = User.get(1)  # Get our mock dev user
    if user:
        login_user(user)
        return redirect(url_for('index'))
    return "Login failed", 401

@app.route('/logout')
@login_required
def logout():
    """Logout route."""
    logout_user()
    return redirect(url_for('index'))

# Register custom template filters
@app.template_filter('price_color')
def price_color_filter(value):
    """Return CSS class based on price change value."""
    try:
        value = float(value)
        return 'text-green-500' if value >= 0 else 'text-red-500'
    except (ValueError, TypeError):
        return 'text-gray-500'

@app.errorhandler(429)
async def ratelimit_handler(e):
    """Handle rate limit exceeded errors."""
    return jsonify(error="Rate limit exceeded. Please try again later."), 429

@app.errorhandler(500)
async def internal_error(e):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify(error="An internal server error occurred. Please try again later."), 500

@app.route('/')
@limiter.exempt  # Main page is exempt from rate limiting
async def index():
    """Render the main dashboard with default values."""
    default_data = {
        'token': 'BTC',
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

@app.route('/chart-data')
@limiter.limit("30 per minute")  # Specific rate limit for chart data
async def chart_data():
    """Handle chart data requests for different timeframes."""
    token = request.args.get('token', 'bitcoin').lower()
    days = int(request.args.get('days', 30))

    try:
        chart_data = await generate_chart_data(token, days)
        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error generating chart data: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/search')
@limiter.limit("20 per minute")  # Specific rate limit for token search
async def search():
    """Handle token search and analysis."""
    token = request.args.get('token', 'bitcoin').lower()
    try:
        # Get market data
        price_data = await get_token_price(token)
        market_data = await get_token_market_data(token)
        signal_data = await get_signal_analysis(token)

        # Calculate trend score (0-100)
        trend_score = min(100, max(0, float(signal_data['signal_strength'])))

        # Format the data for template
        template_data = {
            'token': token.upper(),
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
            'dca_recommendation': signal_data['dca_recommendation'],
            'chart_data': await generate_chart_data(token)
        }

        return render_template('dashboard.html', **template_data)

    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        error_data = {
            'token': token.upper(),
            'error': f"Error analyzing {token.upper()}: {str(e)}",
            'price': 0.0,
            'price_change': 0.0,
            'signal_strength': 0,
            'signal_description': 'Error occurred',
            'trend_score': 0,
            'trend_direction': 'Error',
            'market_status': 'Error',
            'rsi': 0,
            'support_1': 0.0,
            'support_2': 0.0,
            'resistance_1': 0.0,
            'resistance_2': 0.0,
            'dca_recommendation': 'Error occurred while analyzing token',
            'chart_data': {'labels': [], 'datasets': []}
        }
        return render_template('dashboard.html', **error_data)

def get_market_status(rsi):
    """Determine market status based on RSI."""
    if rsi >= 70:
        return "Overbought 🔴"
    elif rsi <= 30:
        return "Oversold 🟢"
    else:
        return "Neutral ⚖️"

async def generate_chart_data(token, days=30):
    """Generate chart data for Chart.js."""
    try:
        # Get historical prices from technical analysis service
        signal_data = await get_signal_analysis(token)

        # Extract prices and format for charting
        prices = [float(price) for price in signal_data.get('historical_prices', [])]

        # Limit data points based on requested days
        prices = prices[-days:]

        # Generate dates for x-axis
        end_date = datetime.now()
        dates = [(end_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
        dates.reverse()

        # Get support and resistance levels
        support_1 = float(signal_data['support_1'].replace('$', '').replace(',', ''))
        resistance_1 = float(signal_data['resistance_1'].replace('$', '').replace(',', ''))

        return {
            'labels': dates[:len(prices)],
            'datasets': [
                {
                    'label': 'Price',
                    'data': prices,
                    'borderColor': '#F97316',
                    'backgroundColor': 'rgba(249, 115, 22, 0.1)',
                    'fill': True,
                    'tension': 0.4
                },
                {
                    'label': 'Support 1',
                    'data': [support_1] * len(prices),
                    'borderColor': '#10B981',
                    'borderDash': [5, 5],
                    'fill': False
                },
                {
                    'label': 'Resistance 1',
                    'data': [resistance_1] * len(prices),
                    'borderColor': '#EF4444',
                    'borderDash': [5, 5],
                    'fill': False
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error generating chart data: {str(e)}")
        return {'labels': [], 'datasets': []}

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return False
        except socket.error:
            return True

if __name__ == '__main__':
    port = 3000
    retries = 3

    while retries > 0:
        if not is_port_in_use(port):
            logger.info(f"Starting development server on port {port}")
            try:
                app.run(
                    host='0.0.0.0',  # Allow external access
                    port=port,
                    debug=True,
                    use_reloader=True,  # Enable auto-reload on code changes
                    threaded=True  # Enable threading
                )
                break
            except Exception as e:
                logger.error(f"Failed to start server: {e}")
                retries -= 1
                port += 1
        else:
            logger.warning(f"Port {port} is in use, trying next port")
            port += 1
            retries -= 1

    if retries == 0:
        logger.error("Could not find an available port to run the server")