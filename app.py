import time
from flask import Flask, render_template, send_from_directory, request
import logging
import socket
from datetime import datetime, timezone
import os
import signal
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        except socket.error:
            return True

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, static_folder='static', static_url_path='/static')

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

            # Initialize market data
            market_data = {
                'current_price': 45000.00,
                'price_change_24h': 2.5,
                'market_cap': 850000000000,
                'volume': 25000000000
            }

            # Initialize price ranges with proper structure
            price_ranges = {
                'day': {'high': 46000.00, 'low': 44000.00},
                'week': {'high': 47000.00, 'low': 43000.00},
                'month': {'high': 48000.00, 'low': 42000.00},
                'quarter': {'high': 50000.00, 'low': 41000.00},
                'year': {'high': 52000.00, 'low': 40000.00}
            }

            template_data = {
                'market_data': market_data,
                'price_ranges': price_ranges,
                'chart_data': [
                    {'timestamp': '2025-02-22', 'price': 44000.00},
                    {'timestamp': '2025-02-23', 'price': 45000.00}
                ],
                'market_insights': {
                    'summary': f"Market analysis for {symbol} loading...",
                    'sentiment': {
                        'score': 0.65,
                        'label': "🟢 Bullish"
                    },
                    'factors': [f"{symbol} price momentum", "Volume analysis", "Technical indicators"],
                    'outlook': f"Market analysis and predictions for {symbol} will be updated every hour."
                },
                'last_updated': datetime.now(timezone.utc),
                'technical_indicators': {
                    'rsi': {'value': 55.0, 'trend': 'Bullish', 'strength': 0.65},
                    'macd': {'signal': 'Buy', 'crossover': 'Bullish', 'trend_strength': 0.7}
                },
                'price_levels': {
                    'support_1': 44000.00,
                    'support_2': 43000.00,
                    'resistance_1': 46000.00,
                    'resistance_2': 47000.00
                },
                'trading_levels': {
                    'optimal_entry': 44500.00,
                    'optimal_exit': 46500.00,
                    'stop_loss': 43500.00
                },
                'ml_predictions': {
                    'next_day': {
                        'rf_prediction': 45500.00,
                        'prophet_prediction': 45700.00,
                        'combined_prediction': 45600.00,
                        'upper_bound': 46000.00,
                        'lower_bound': 45000.00
                    }
                },
                'confidence_score': 75.0,
                'signal': 'Buy',
                'signal_strength': 65.0,
                'trend_direction': 'Upward'
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
    try:
        port = 3000
        if is_port_in_use(port):
            logger.warning(f"Port {port} is in use, attempting to free it...")
            if not kill_process_on_port(port):
                raise RuntimeError(f"Could not free port {port}")
        logger.info(f"Starting Flask application on port {port}...")
        app = create_app()
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        raise