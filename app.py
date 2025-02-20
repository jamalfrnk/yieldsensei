from flask import Flask, render_template, request, jsonify
from services.technical_analysis import get_signal_analysis
from services.coingecko_service import get_token_price, get_token_market_data
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Register custom template filters
@app.template_filter('price_color')
def price_color_filter(value):
    """Return CSS class based on price change value."""
    try:
        value = float(value)
        return 'text-green-500' if value >= 0 else 'text-red-500'
    except (ValueError, TypeError):
        return 'text-gray-500'

@app.route('/')
def index():
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

@app.route('/search')
def search():
    """Handle token search and analysis."""
    token = request.args.get('token', 'bitcoin').lower()
    try:
        # Get market data
        price_data = get_token_price(token)
        market_data = get_token_market_data(token)
        signal_data = get_signal_analysis(token)

        # Calculate trend score (0-100)
        trend_score = min(100, max(0, signal_data['signal_strength']))

        return render_template('dashboard.html',
            token=token.upper(),
            price=price_data['usd'],
            price_change=price_data['usd_24h_change'],
            signal_strength=signal_data['signal_strength'],
            signal_description=signal_data['signal'],
            trend_score=trend_score,
            trend_direction=signal_data['trend_direction'],
            market_status=get_market_status(signal_data['rsi']),
            rsi=signal_data['rsi'],
            support_1=signal_data['support_1'],
            support_2=signal_data['support_2'],
            resistance_1=signal_data['resistance_1'],
            resistance_2=signal_data['resistance_2'],
            dca_recommendation=signal_data['dca_recommendation'],
            chart_data=generate_chart_data(token)
        )
    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        error_data = {
            'token': token.upper(),
            'error': str(e),
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

def generate_chart_data(token):
    """Generate chart data for Chart.js."""
    try:
        # Get historical prices from technical analysis service
        signal_data = get_signal_analysis(token)
        prices = signal_data.get('historical_prices', [])
        levels = {
            'support_1': signal_data['support_1'],
            'resistance_1': signal_data['resistance_1']
        }

        return {
            'labels': [f"Day {i+1}" for i in range(len(prices))],
            'datasets': [
                {
                    'label': 'Price',
                    'data': prices,
                    'borderColor': '#F97316',
                    'fill': False
                },
                {
                    'label': 'Support 1',
                    'data': [levels['support_1']] * len(prices),
                    'borderColor': '#10B981',
                    'borderDash': [5, 5]
                },
                {
                    'label': 'Resistance 1',
                    'data': [levels['resistance_1']] * len(prices),
                    'borderColor': '#EF4444',
                    'borderDash': [5, 5]
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error generating chart data: {str(e)}")
        return {'labels': [], 'datasets': []}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)