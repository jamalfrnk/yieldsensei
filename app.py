import logging
import sys

# Configure logging with full tracebacks
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

try:
    logger.info("Importing Flask...")
    from flask import Flask
    from werkzeug.middleware.proxy_fix import ProxyFix
    logger.info("Flask imported successfully")
except Exception as e:
    logger.critical(f"Failed to import Flask: {str(e)}", exc_info=True)
    sys.exit(1)

try:
    logger.info("Creating Flask app...")
    app = Flask(__name__)

    # Configure Flask for proxy support
    logger.info("Configuring proxy support...")
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    original_wsgi_app = app.wsgi_app
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,      # Number of proxy servers
        x_proto=1,    # SSL termination happens at the proxy
        x_host=1,     # Host header is set by the proxy
        x_prefix=1    # Any URL prefix is set by the proxy
    )
    logger.info(f"WSGI app before proxy: {original_wsgi_app}")
    logger.info(f"WSGI app after proxy: {app.wsgi_app}")
    logger.info("Proxy support configured successfully")

    @app.route('/')
    def index():
        return "Hello World - Server is running!"

    if __name__ == '__main__':
        try:
            # Use Flask's development server with detailed error reporting
            logger.info("Starting Flask development server on port 5000...")
            app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
        except Exception as e:
            logger.critical(f"Application startup failed: {str(e)}", exc_info=True)
            sys.exit(1)

except Exception as e:
    logger.critical(f"Failed to create Flask application: {str(e)}", exc_info=True)
    sys.exit(1)