import logging
import sys
import socket

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello World! Minimal Flask Test Server"

if __name__ == '__main__':
    try:
        # Check if port is already in use
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('0.0.0.0', 5000))
        if result == 0:
            logger.error("Port 5000 is already in use!")
            sys.exit(1)
        sock.close()

        logger.info("Starting minimal Flask server...")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=False
        )
    except Exception as e:
        logger.error(f"Failed to start Flask server: {str(e)}", exc_info=True)
        raise