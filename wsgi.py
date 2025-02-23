
from waitress import serve
from app import app
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('waitress')

if __name__ == "__main__":
    try:
        logger.info("Starting production server on port 8080...")
        serve(app, host='0.0.0.0', port=8080, threads=6)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
