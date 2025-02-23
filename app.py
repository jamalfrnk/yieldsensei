import logging
import sys
import os
import socket
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required
from auth import auth
from models import db, User

# Configure logging with full tracebacks
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

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
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = False

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Initialize SQLAlchemy
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/docs')
    def documentation():
        return render_template('documentation.html')

    @app.route('/telegram')
    def telegram():
        return render_template('telegram.html')

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