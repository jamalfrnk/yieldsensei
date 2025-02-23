from flask import Flask
import logging

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
    return "Hello World! Flask Test Server is running!"

if __name__ == '__main__':
    try:
        logger.info("Starting Flask test server...")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {str(e)}", exc_info=True)
        raise
