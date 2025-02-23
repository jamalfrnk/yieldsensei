from waitress import serve
from app import app
import logging
import socket
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('waitress')

def check_port_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except OSError:
        return False

if __name__ == "__main__":
    port = 5000
    if not check_port_available(port):
        logger.error(f"Port {port} is already in use!")
        sys.exit(1)

    try:
        logger.info(f"Starting production server on port {port}...")
        serve(app, host='0.0.0.0', port=port, threads=6)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)