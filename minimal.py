import logging
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello World! Minimal Flask Test Server"

if __name__ == '__main__':
    try:
        logger.info("Starting minimal Flask server...")
        app.run(
            host='0.0.0.0',
            port=8080,
            debug=False,
            use_reloader=False,
            threaded=False
        )
    except Exception as e:
        logger.error(f"Failed to start Flask server: {str(e)}", exc_info=True)
        raise