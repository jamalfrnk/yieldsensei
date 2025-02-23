import os
import logging
from flask import Flask, render_template, send_from_directory

# Configure detailed logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Set to DEBUG for more detailed logs
)
logger = logging.getLogger(__name__)

# Initialize Flask app with explicit static folder
app = Flask(__name__, 
    static_folder='static',
    static_url_path='/static'
)

# Configure Flask app
app.config['SECRET_KEY'] = os.urandom(24)  # Add secret key for forms
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Enable template auto-reload

@app.route('/')
def index():
    try:
        logger.debug("Attempting to render index page")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/dashboard')
def dashboard():
    try:
        logger.debug("Attempting to render dashboard page")
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering dashboard page: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        logger.debug(f"Attempting to serve static file: {filename}")
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 404

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal server error"), 500

if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/assets', exist_ok=True)

    # Start server
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)