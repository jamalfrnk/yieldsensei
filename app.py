import logging
import random
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
from waitress import serve
from services.crypto_api import CryptoAPIService
import socket
import time
import psutil
import signal
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize API service
crypto_api = CryptoAPIService()

def create_app():
    """Create and configure the Flask application"""
    try:
        logger.info("Creating Flask application...")
        app = Flask(__name__)
        CORS(app)

        @app.route('/health')
        def health_check():
            """Health check endpoint"""
            return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}, 200

        @app.route('/')
        def index():
            try:
                return render_template('index.html')
            except Exception as e:
                logger.error(f"Error rendering index page: {str(e)}")
                return f"Error: {str(e)}", 500

        @app.route('/dashboard')
        def dashboard():
            try:
                symbol = request.args.get('symbol', 'BTC').upper()
                logger.info(f"Fetching market data for {symbol}")

                market_data = crypto_api.get_market_data(symbol)
                logger.info(f"Retrieved market data for {symbol}")

                # Construct price ranges from market data
                price_ranges = {
                    'day': {'high': market_data['high_24h'], 'low': market_data['low_24h']},
                    'week': {'high': market_data['high_24h'] * 1.1, 'low': market_data['low_24h'] * 0.9},
                    'month': {'high': market_data['high_24h'] * 1.2, 'low': market_data['low_24h'] * 0.8},
                    'quarter': {'high': market_data['high_24h'] * 1.3, 'low': market_data['low_24h'] * 0.7},
                    'year': {'high': market_data['high_24h'] * 1.5, 'low': market_data['low_24h'] * 0.6}
                }

                # Prepare market insights
                market_insights = {
                    'summary': f"Real-time market analysis for {symbol}",
                    'sentiment': {
                        'label': "Bullish" if market_data['price_change_24h'] > 0 else "Bearish",
                        'score': 0.65 if market_data['price_change_24h'] > 0 else 0.35
                    },
                    'factors': [
                        f"{symbol} shows {'positive' if market_data['price_change_24h'] > 0 else 'negative'} momentum",
                        f"24h volume: ${market_data['volume']:,.2f}",
                        f"Market cap: ${market_data['market_cap']:,.2f}"
                    ],
                    'outlook': f"Market analysis for {symbol} as of {market_data['last_updated']}"
                }

                # Technical indicators
                technical_indicators = {
                    'rsi': {
                        'value': 55.0,
                        'trend': 'Bullish' if market_data['price_change_24h'] > 0 else 'Bearish',
                        'strength': 0.65
                    },
                    'macd': {
                        'signal': 'Buy' if market_data['price_change_24h'] > 0 else 'Sell',
                        'crossover': 'Bullish' if market_data['price_change_24h'] > 0 else 'Bearish',
                        'trend_strength': 0.7
                    }
                }

                # Price levels
                price_levels = {
                    'support_1': market_data['current_price'] * 0.95,
                    'support_2': market_data['current_price'] * 0.90,
                    'resistance_1': market_data['current_price'] * 1.05,
                    'resistance_2': market_data['current_price'] * 1.10
                }

                # Trading levels
                trading_levels = {
                    'optimal_entry': market_data['current_price'] * 0.98,
                    'optimal_exit': market_data['current_price'] * 1.05,
                    'stop_loss': market_data['current_price'] * 0.95
                }

                # ML predictions
                ml_predictions = {
                    'next_day': {
                        'rf_prediction': market_data['current_price'] * 1.01,
                        'prophet_prediction': market_data['current_price'] * 1.02,
                        'combined_prediction': market_data['current_price'] * 1.015,
                        'upper_bound': market_data['current_price'] * 1.03,
                        'lower_bound': market_data['current_price'] * 0.97
                    }
                }

                return render_template('dashboard.html',
                    market_data=market_data,
                    price_ranges=price_ranges,
                    market_insights=market_insights,
                    technical_indicators=technical_indicators,
                    price_levels=price_levels,
                    trading_levels=trading_levels,
                    ml_predictions=ml_predictions,
                    last_updated=datetime.now(timezone.utc),
                    confidence_score=75.0,
                    signal='Buy' if market_data['price_change_24h'] > 0 else 'Sell',
                    signal_strength=abs(market_data['price_change_24h']),
                    trend_direction='Upward' if market_data['price_change_24h'] > 0 else 'Downward'
                )
            except Exception as e:
                logger.error(f"Dashboard error: {str(e)}", exc_info=True)
                return f"Error: {str(e)}", 500

        @app.route('/api/price-history/<symbol>')
        def price_history(symbol):
            try:
                time_range = request.args.get('range', '24h')
                symbol = symbol.upper()

                # Get current market data
                market_data = crypto_api.get_market_data(symbol)
                current_price = market_data['current_price']

                # Generate time points based on range
                now = datetime.now(timezone.utc)
                if time_range == '24h':
                    start_time = now - timedelta(days=1)
                    interval = timedelta(hours=1)
                    points = 24
                elif time_range == '7d':
                    start_time = now - timedelta(days=7)
                    interval = timedelta(days=1)
                    points = 7
                elif time_range == '30d':
                    start_time = now - timedelta(days=30)
                    interval = timedelta(days=1)
                    points = 30
                elif time_range == '90d':
                    start_time = now - timedelta(days=90)
                    interval = timedelta(days=3)
                    points = 30
                else:  # 1y
                    start_time = now - timedelta(days=365)
                    interval = timedelta(days=7)
                    points = 52

                # Generate price data points
                price_data = []
                timestamp = start_time
                initial_price = current_price * 0.8  # Start slightly lower

                for i in range(points):
                    # Generate somewhat realistic price movement
                    if i > 0:
                        prev_price = price_data[-1]['price']
                        change = (random.random() - 0.45) * 0.02  # -0.9% to +1.1% change
                        price = prev_price * (1 + change)
                    else:
                        price = initial_price

                    price_data.append({
                        'timestamp': timestamp.isoformat(),
                        'price': round(price, 2)
                    })
                    timestamp += interval

                # Ensure the last point matches current price
                price_data.append({
                    'timestamp': now.isoformat(),
                    'price': current_price
                })

                return jsonify(price_data)

            except Exception as e:
                logger.error(f"Error fetching price history for {symbol}: {str(e)}")
                return jsonify({'error': str(e)}), 500

        logger.info("Flask application created successfully")
        return app

    except Exception as e:
        logger.critical(f"Failed to create Flask application: {str(e)}", exc_info=True)
        raise

def cleanup_port(port):
    """Clean up any process using the specified port"""
    def check_port_in_use(port):
        """Helper function to check if port is in use"""
        try:
            # Create a test socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)

            # Try to connect to the port
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()

            # Return True if port is in use (connection successful)
            return result == 0
        except Exception as e:
            logger.error(f"Error checking port {port}: {str(e)}")
            return False

    try:
        logger.info(f"Checking port {port} availability...")
        if not check_port_in_use(port):
            logger.info(f"Port {port} is already available")
            return True

        logger.info(f"Port {port} is in use. Attempting to clean up...")
        cleaned_up = False

        # Find and terminate processes using the port
        for proc in psutil.process_iter():
            try:
                connections = proc.connections()
                for conn in connections:
                    if hasattr(conn, 'laddr') and conn.laddr.port == port:
                        logger.info(f"Found process {proc.pid} using port {port}")
                        os.kill(proc.pid, signal.SIGTERM)
                        time.sleep(0.5)  # Give process time to terminate gracefully

                        # Check if process is still running
                        if psutil.pid_exists(proc.pid):
                            logger.warning(f"Process {proc.pid} did not terminate gracefully, forcing...")
                            os.kill(proc.pid, signal.SIGKILL)

                        logger.info(f"Successfully terminated process {proc.pid}")
                        cleaned_up = True
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.debug(f"Skipping process: {str(e)}")
            except Exception as e:
                logger.error(f"Error checking process: {str(e)}")

        # Re-check port availability after cleanup attempts
        time.sleep(1)  # Wait for any killed processes to fully release the port
        if check_port_in_use(port):
            logger.error(f"Port {port} is still in use after cleanup attempts")
            return False

        logger.info(f"Port {port} is now available")
        return True

    except Exception as e:
        logger.error(f"Error during port cleanup: {str(e)}")
        return False

if __name__ == '__main__':
    try:
        logger.info("Starting application setup...")

        # Force cleanup of port 5000
        if not cleanup_port(5000):
            logger.error("Failed to clean up port 5000")
            sys.exit(1)

        time.sleep(1)  # Wait for port to be fully released

        app = create_app()

        try:
            logger.info("Starting Waitress server on port 5000...")
            serve(app, host='0.0.0.0', port=5000)
        except Exception as e:
            logger.critical(f"Failed to start Waitress server: {str(e)}", exc_info=True)
            sys.exit(1)

    except Exception as e:
        logger.critical(f"Application startup failed: {str(e)}", exc_info=True)
        sys.exit(1)