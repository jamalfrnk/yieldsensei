from flask import Flask, render_template
import logging
import sys
from models import db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db.init_app(app)

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {e}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/dashboard')
def dashboard():
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}", exc_info=True)
        return "Error loading dashboard", 500

@app.route('/docs')
def documentation():
    try:
        return render_template('docs.html')
    except Exception as e:
        logger.error(f"Error rendering documentation: {e}", exc_info=True)
        return "Error loading documentation", 500

@app.route('/telegram')
def telegram():
    try:
        return render_template('telegram.html')
    except Exception as e:
        logger.error(f"Error rendering telegram page: {e}", exc_info=True)
        return "Error loading telegram page", 500


if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
        logger.info("Starting Flask development server...")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)