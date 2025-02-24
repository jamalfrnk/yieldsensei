from flask import Flask, jsonify
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    logger.info("Creating Flask application...")
    app = Flask(__name__)

    # Basic configuration
    app.config['SECRET_KEY'] = 'dev-key'

    # Health check route
    @app.route('/health')
    def health_check():
        logger.info("Health check endpoint called")
        return jsonify({"status": "healthy"})

    # Simple test route
    @app.route('/')
    def index():
        logger.info("Index endpoint called")
        return jsonify({"status": "ok", "message": "Flask server is running"})

    # Error handlers (from original)
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"status": "error", "message": "Not Found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"status": "error", "message": "Internal Server Error"}), 500

    logger.info("Flask application created successfully")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)