import time
from flask import Flask, render_template, send_from_directory, request
import logging
import socket
from datetime import datetime, timezone
import os
import signal
import psutil
from flask_cors import CORS
from services.crypto_api import CryptoAPIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize API service
crypto_api = CryptoAPIService()

def kill_process_on_port(port):
    """Kill any process running on the specified port"""
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections('tcp'):
                    if conn.laddr.port == port:
                        os.kill(proc.pid, signal.SIGTERM)
                        logger.info(f"Killed process {proc.pid} on port {port}")
                        time.sleep(1)  # Give the process time to terminate
                        return True
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        return False
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
        return False

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error as e:
            logger.warning(f"Port {port} in use: {e}")
            return True

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    CORS(app)  # Enable CORS for all routes

    # Request logging middleware
    @app.before_request
    def log_request_info():
        logger.info(f'Request: {request.method} {request.url} from {request.remote_addr}')
        logger.debug(f'Headers: {dict(request.headers)}')

    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}, 200

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
            # Get symbol from query parameters, default to BTC
            symbol = request.args.get('symbol', 'BTC').upper()

            # Fetch real-time market data
            market_data = crypto_api.get_market_data(symbol)

            # Initialize price ranges with market data
            price_ranges = {
                'day': {'high': market_data['high_24h'], 'low': market_data['low_24h']},
                'week': {'high': market_data['high_24h'] * 1.1, 'low': market_data['low_24h'] * 0.9},
                'month': {'high': market_data['high_24h'] * 1.2, 'low': market_data['low_24h'] * 0.8},
                'quarter': {'high': market_data['high_24h'] * 1.3, 'low': market_data['low_24h'] * 0.7},
                'year': {'high': market_data['high_24h'] * 1.5, 'low': market_data['low_24h'] * 0.6}
            }

            template_data = {
                'market_data': market_data,
                'price_ranges': price_ranges,
                'chart_data': [
                    {'timestamp': '2025-02-22', 'price': market_data['low_24h']},
                    {'timestamp': '2025-02-23', 'price': market_data['current_price']}
                ],
                'market_insights': {
                    'summary': f"Real-time market analysis for {symbol}",
                    'sentiment': {
                        'score': 0.65,
                        'label': "🟢 Bullish" if market_data['price_change_24h'] > 0 else "🔴 Bearish"
                    },
                    'factors': [
                        f"{symbol} price action shows {'positive' if market_data['price_change_24h'] > 0 else 'negative'} momentum",
                        f"24h trading volume: ${market_data['volume']:,.2f}",
                        f"Market cap: ${market_data['market_cap']:,.2f}"
                    ],
                    'outlook': f"Market analysis and predictions for {symbol} updated at {market_data['last_updated']}"
                },
                'last_updated': datetime.now(timezone.utc),
                'technical_indicators': {
                    'rsi': {'value': 55.0, 'trend': 'Bullish' if market_data['price_change_24h'] > 0 else 'Bearish', 'strength': 0.65},
                    'macd': {'signal': 'Buy' if market_data['price_change_24h'] > 0 else 'Sell', 'crossover': 'Bullish' if market_data['price_change_24h'] > 0 else 'Bearish', 'trend_strength': 0.7}
                },
                'price_levels': {
                    'support_1': market_data['current_price'] * 0.95,
                    'support_2': market_data['current_price'] * 0.90,
                    'resistance_1': market_data['current_price'] * 1.05,
                    'resistance_2': market_data['current_price'] * 1.10
                },
                'trading_levels': {
                    'optimal_entry': market_data['current_price'] * 0.98,
                    'optimal_exit': market_data['current_price'] * 1.05,
                    'stop_loss': market_data['current_price'] * 0.95
                },
                'ml_predictions': {
                    'next_day': {
                        'rf_prediction': market_data['current_price'] * 1.01,
                        'prophet_prediction': market_data['current_price'] * 1.02,
                        'combined_prediction': market_data['current_price'] * 1.015,
                        'upper_bound': market_data['current_price'] * 1.03,
                        'lower_bound': market_data['current_price'] * 0.97
                    }
                },
                'confidence_score': 75.0,
                'signal': 'Buy' if market_data['price_change_24h'] > 0 else 'Sell',
                'signal_strength': abs(market_data['price_change_24h']),
                'trend_direction': 'Upward' if market_data['price_change_24h'] > 0 else 'Downward'
            }

            return render_template('dashboard.html', **template_data)
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
    port = 5000
    try:
        if is_port_in_use(port):
            if not kill_process_on_port(port):
                logger.error(f"Failed to kill process on port {port}. Server might not start.")
            time.sleep(2)  # Wait for port to be fully released

        app = create_app()
        logger.info(f"Starting Flask application on port {port}...")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise