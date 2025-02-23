from waitress import serve
from app import app
import logging
import socket
import sys
import os
import time
import psutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('waitress')

def find_process_using_port(port):
    """Find and log information about process using the specified port."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    logger.error(f"Port {port} is being used by process: {proc.info}")
                    return proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def check_port_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except OSError:
        pid = find_process_using_port(port)
        if pid:
            logger.error(f"Port {port} is being used by PID: {pid}")
        return False

if __name__ == "__main__":
    port = 5000
    logger.info(f"Current process ID: {os.getpid()}")

    # Add retry logic for port availability
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        if check_port_available(port):
            break
        logger.warning(f"Port {port} is busy, waiting {retry_delay} seconds before retry {attempt + 1}/{max_retries}")
        time.sleep(retry_delay)

    if not check_port_available(port):
        logger.error(f"Port {port} is still in use after {max_retries} attempts!")
        sys.exit(1)

    try:
        logger.info(f"Starting production server on port {port}...")
        serve(app, host='0.0.0.0', port=port, threads=6)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)