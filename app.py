from flask import Flask, render_template, request, jsonify
import asyncio
from services.technical_analysis import get_signal_analysis
from services.coingecko_service import get_token_price, get_token_market_data
import logging
from datetime import datetime, timedelta
from asgiref.wsgi import WsgiToAsgi

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)