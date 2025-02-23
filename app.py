import logging
import sys
import os
import socket

# Configure logging with full tracebacks
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

try:
    logger.info("Importing Flask...")
    from flask import Flask
    logger.info("Flask imported successfully")
except Exception as e:
    logger.critical(f"Failed to import Flask: {str(e)}", exc_info=True)
    sys.exit(1)

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error as e:
            logger.error(f"Port {port} check failed: {str(e)}")
            return True

try:
    logger.info("Creating Flask app...")
    app = Flask(__name__)
    app.config['DEBUG'] = False

    @app.route('/')
    def index():
        return "Hello World - Server is running!"

except Exception as e:
    logger.critical(f"Failed to create Flask application: {str(e)}", exc_info=True)
    sys.exit(1)

if __name__ == '__main__':
    try:
        port = 5000  # ALWAYS use port 5000 for Replit
        if is_port_in_use(port):
            logger.error(f"Port {port} is already in use!")
            sys.exit(1)

        logger.info(f"Starting Flask server on port {port}...")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            threaded=False
        )
    except Exception as e:
        logger.critical(f"Application startup failed: {str(e)}", exc_info=True)
        sys.exit(1)