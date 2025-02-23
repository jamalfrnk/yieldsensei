from flask import Flask, render_template, send_from_directory
import logging
import sys
import os
import signal
import socket
from models import db

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.environ.get('FLASK_ENV') == 'production' else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('flask_app.log')
    ]
)
logger = logging.getLogger(__name__)

def check_port_available(port):
    """Check if a port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except OSError as e:
        logger.error(f"Error checking port availability: {e}")
        return False

def cleanup_handler(signum, frame):
    """Handle cleanup when the app is shutting down."""
    logger.info("Received signal to shutdown. Cleaning up...")
    sys.exit(0)

def create_app():
    try:
        # Create Flask app
        app = Flask(__name__, 
                   static_folder='static',
                   template_folder='templates')

        # Configure app
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        # Production configurations
        if os.environ.get('FLASK_ENV') == 'production':
            app.config['SESSION_COOKIE_SECURE'] = True
            app.config['SESSION_COOKIE_HTTPONLY'] = True
            app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

        # Initialize extensions
        db.init_app(app)

        # Error handlers
        @app.errorhandler(404)
        def not_found_error(error):
            logger.warning(f"404 error: {error}")
            return render_template('errors/404.html'), 404

        @app.errorhandler(500)
        def internal_error(error):
            logger.error(f"500 error: {error}", exc_info=True)
            return render_template('errors/500.html'), 500

        # Register routes
        @app.route('/')
        def index():
            try:
                return render_template('index.html')
            except Exception as e:
                logger.error(f"Error rendering index: {e}", exc_info=True)
                return f"Error: {str(e)}", 500

        @app.route('/dashboard')
        def dashboard():
            try:
                return render_template('dashboard.html')
            except Exception as e:
                logger.error(f"Error rendering dashboard: {e}", exc_info=True)
                return "Error loading dashboard", 500

        @app.route('/docs')
        def documentation():
            try:
                return render_template('documentation.html')
            except Exception as e:
                logger.error(f"Error rendering documentation: {e}", exc_info=True)
                return "Error loading documentation", 500

        @app.route('/telegram')
        def telegram():
            try:
                return render_template('telegram.html')
            except Exception as e:
                logger.error(f"Error rendering telegram page: {e}", exc_info=True)
                return "Error loading telegram page", 500

        # Ensure the static folder exists
        os.makedirs(app.static_folder, exist_ok=True)

        logger.info("Application successfully created")
        return app

    except Exception as e:
        logger.critical(f"Failed to create application: {e}", exc_info=True)
        raise

# Create the application instance
app = create_app()

if __name__ == '__main__':
    try:
        # Set up signal handlers
        signal.signal(signal.SIGINT, cleanup_handler)
        signal.signal(signal.SIGTERM, cleanup_handler)

        port = 5000
        if not check_port_available(port):
            logger.error(f"Port {port} is already in use! Please free the port and try again.")
            sys.exit(1)

        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
        logger.info("Starting Flask development server...")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)