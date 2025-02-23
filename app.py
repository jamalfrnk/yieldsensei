from flask import Flask, render_template
import os
import logging
import sys

# Configure logging with console and file output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('flask_app.log')
    ]
)
logger = logging.getLogger(__name__)

try:
    # Create Flask app
    logger.info("Creating Flask app...")
    app = Flask(__name__)

    # Basic configuration
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['DEBUG'] = True

    logger.info("Checking template directory...")
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    if not os.path.exists(template_dir):
        logger.error(f"Template directory not found at: {template_dir}")
        raise FileNotFoundError(f"Template directory missing: {template_dir}")

    @app.route('/')
    def index():
        try:
            logger.info("Attempting to render index.html")
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering index.html: {str(e)}", exc_info=True)
            return f"Error loading page: {str(e)}", 500

    @app.route('/health')
    def health():
        return "Flask server is running!", 200

    @app.route('/dashboard')
    def dashboard():
        try:
            return render_template('dashboard.html')
        except Exception as e:
            logger.error(f"Error rendering dashboard: {str(e)}", exc_info=True)
            return f"Error loading dashboard: {str(e)}", 500

    @app.route('/docs')
    def documentation():
        try:
            return render_template('documentation.html')
        except Exception as e:
            logger.error(f"Error rendering documentation: {str(e)}", exc_info=True)
            return f"Error loading documentation: {str(e)}", 500

    @app.route('/telegram')
    def telegram():
        try:
            return render_template('telegram.html')
        except Exception as e:
            logger.error(f"Error rendering telegram page: {str(e)}", exc_info=True)
            return f"Error loading telegram page: {str(e)}", 500

except Exception as e:
    logger.critical(f"Failed to initialize Flask app: {str(e)}", exc_info=True)
    sys.exit(1)

if __name__ == '__main__':
    try:
        logger.info("Starting Flask server on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start Flask server: {str(e)}", exc_info=True)
        sys.exit(1)