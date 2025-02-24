import logging
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

@app.route('/ping')
def ping():
    return "pong"

if __name__ == '__main__':
    app.run(
        host='0.0.0.0', 
        port=5000
    )