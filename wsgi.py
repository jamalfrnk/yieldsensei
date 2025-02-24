from waitress import serve
from app import app
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('waitress')

if __name__ == "__main__":
    try:
        # Log startup information
        logger.info("Starting server initialization...")
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Attempting to start server on port {port}")

        # Start the server
        serve(app, host='0.0.0.0', port=port)
    except Exception as e:
        logger.exception(f"Failed to start server: {str(e)}")
        sys.exit(1)