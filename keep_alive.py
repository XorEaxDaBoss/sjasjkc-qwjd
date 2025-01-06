from flask import Flask, jsonify, send_from_directory, make_response
from threading import Thread
import socket
import os
import logging
import psutil
import time
from waitress import serve

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='webapp')
PORT = int(os.getenv('PORT', 8080))
START_TIME = time.time()

# Store cards in memory (you might want to use a proper database later)
webapp_data = {}

@app.route('/')
def index():
    """Serve the webapp"""
    response = make_response(send_from_directory(app.static_folder, 'index.html'))
    response.headers['Content-Security-Policy'] = (
        "default-src 'self' https://telegram.org https://*.telegram.org https://t.me https://*.t.me data: blob:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://telegram.org https://*.telegram.org https://t.me https://*.t.me https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://telegram.org https://*.telegram.org https://t.me https://*.t.me https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https://telegram.org https://*.telegram.org https://t.me https://*.t.me https://cdnjs.cloudflare.com;"
    )
    return response

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    response = make_response(send_from_directory(app.static_folder, path))
    if path.endswith('.js'):
        response.headers['Content-Type'] = 'application/javascript'
    elif path.endswith('.css'):
        response.headers['Content-Type'] = 'text/css'
    return response

@app.route('/api/cards/<user_id>')
def get_cards(user_id):
    """Get cards for a user"""
    cards = webapp_data.get(user_id, [])
    logger.info(f"Getting cards for user {user_id}: {len(cards)} cards found")
    return jsonify({'cards': cards})

@app.route('/health')
def health():
    """Health check endpoint with system metrics"""
    process = psutil.Process()
    uptime = time.time() - START_TIME
    
    metrics = {
        'status': 'healthy',
        'uptime_seconds': int(uptime),
        'uptime_hours': round(uptime / 3600, 2),
        'memory_usage_mb': round(process.memory_info().rss / 1024 / 1024, 2),
        'cpu_percent': process.cpu_percent(),
        'threads': process.num_threads()
    }
    
    logger.info(f"Health check: {metrics}")
    return jsonify(metrics)

def run():
    if os.getenv('RENDER'):
        logger.info("Starting production server with Waitress...")
        serve(app, host='0.0.0.0', port=PORT, threads=4, connection_limit=100, cleanup_interval=30)
    else:
        logger.info("Starting development server...")
        app.run(host='0.0.0.0', port=PORT)

def keep_alive():
    try:
        server = Thread(target=run, name="KeepAliveServer")
        server.start()
        logger.info(f"Keep-alive server started on port {PORT}")
    except Exception as e:
        logger.error(f"Error starting keep-alive server: {e}")