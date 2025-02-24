from app import create_app
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = create_app()

if __name__ == "__main__":
    try:
        logger.info("Starting development server on http://0.0.0.0:5000")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise