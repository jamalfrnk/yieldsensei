import logging
import os
from flask import Flask, render_template, send_from_directory
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from models import db, User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    try:
        # Create Flask app
        app = Flask(__name__)
        logger.info("Creating Flask application...")

        # Configure app using environment variables
        app.config['SECRET_KEY'] = 'dev'
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['DEBUG'] = True

        logger.info("Initializing database connection...")
        # Initialize extensions
        db.init_app(app)

        with app.app_context():
            # Create database tables
            db.create_all()
            logger.info("Database tables created successfully")

        # Initialize Login Manager
        login_manager = LoginManager()
        login_manager.login_view = 'auth.login'
        login_manager.init_app(app)

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

        # Register blueprints
        from auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint)

        # Test route
        @app.route('/ping')
        def ping():
            logger.info("Ping endpoint accessed")
            return "pong"

        # Static files route
        @app.route('/static/<path:filename>')
        def static_files(filename):
            logger.info(f"Serving static file: {filename}")
            return send_from_directory('static', filename)

        # Routes
        @app.route('/')
        def index():
            logger.info("Handling request for index page")
            try:
                return render_template('index.html')
            except Exception as e:
                logger.error(f"Error rendering index page: {str(e)}")
                return "Welcome to YieldSensei! (Template rendering error)", 500

        logger.info("Application successfully configured")
        return app

    except Exception as e:
        logger.error(f"Error creating application: {str(e)}")
        raise

if __name__ == '__main__':
    app = create_app()
    logger.info("Starting Flask development server...")
    app.run(
        host='0.0.0.0', 
        port=5000,
        debug=True
    )