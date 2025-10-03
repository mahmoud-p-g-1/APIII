# app.py

import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import traceback

# Import configuration
from config import Config

# Import API blueprints
from api.measurements.routes import measurements_bp
from api.scraping.routes import scraping_bp
from api.clothing.routes import clothing_bp

# Import workers
from workers.measurement_worker import start_measurement_worker
from workers.clothing_worker import start_clothing_worker

# Import utilities
from firebase_config import verify_token
from queue_manager import queue_manager

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Register API blueprints
app.register_blueprint(measurements_bp, url_prefix='/api/measurements')
app.register_blueprint(scraping_bp, url_prefix='/api/scraping')
app.register_blueprint(clothing_bp, url_prefix='/api/clothing')

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    return jsonify({
        'message': 'Professional Measurement & Clothing Analysis API',
        'version': '2.0.0',
        'services': {
            'body_measurements': '/api/measurements/',
            'clothing_measurements': '/api/clothing/',
            'web_scraping': '/api/scraping/'
        },
        'features': [
            'Professional body measurements with VTON optimization',
            'Clothing measurement and size recommendation',
            'Google Vision API integration for clothing analysis',
            'Forbidden item filtering',
            'Firebase authentication and storage',
            'Real-time job processing with queue system'
        ],
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check queue manager
        queue_size = queue_manager.get_queue_size()
        
        # Check if required directories exist
        required_dirs = [
            'measurement_data',
            'clothing_data',
            'measurement_modules',
            'clothing_modules'
        ]
        
        dir_status = {}
        for dir_name in required_dirs:
            dir_status[dir_name] = os.path.exists(dir_name)
        
        # Check if service account exists
        service_account_exists = os.path.exists('firebase-service-account.json')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'queue_size': queue_size,
            'directories': dir_status,
            'firebase_service_account': service_account_exists,
            'workers': {
                'measurement_worker': 'running',
                'clothing_worker': 'running'
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/queue/status', methods=['GET'])
def queue_status():
    """Get queue status"""
    try:
        queue_size = queue_manager.get_queue_size()
        
        return jsonify({
            'queue_size': queue_size,
            'status': 'active',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/auth/verify', methods=['POST'])
def verify_auth_token():
    """Verify authentication token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        user_info = verify_token(token)
        
        if user_info:
            return jsonify({
                'valid': True,
                'user_id': user_info['user_id'],
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'valid': False,
                'error': 'Invalid token'
            }), 401
            
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': {
            'measurements': '/api/measurements/',
            'clothing': '/api/clothing/',
            'scraping': '/api/scraping/',
            'health': '/health',
            'queue_status': '/api/queue/status'
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'timestamp': datetime.now().isoformat()
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all other exceptions"""
    print(f"[APP ERROR] Unhandled exception: {str(e)}")
    print(f"[APP ERROR] Traceback: {traceback.format_exc()}")
    
    return jsonify({
        'error': 'Application error',
        'message': str(e),
        'timestamp': datetime.now().isoformat()
    }), 500

@app.before_request
def log_request_info():
    """Log request information"""
    if request.endpoint not in ['health', 'home']:  # Skip logging for health checks
        print(f"\n[REQUEST] {request.method} {request.path}")
        print(f"[REQUEST] User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        print(f"[REQUEST] Content-Type: {request.headers.get('Content-Type', 'None')}")
        if request.method == 'POST' and request.is_json:
            print(f"[REQUEST] JSON Keys: {list(request.json.keys()) if request.json else 'None'}")

@app.after_request
def log_response_info(response):
    """Log response information"""
    if request.endpoint not in ['health', 'home']:  # Skip logging for health checks
        print(f"[RESPONSE] Status: {response.status_code}")
        print(f"[RESPONSE] Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
    
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response

def initialize_directories():
    """Initialize required directories"""
    directories = [
        'measurement_data',
        'measurement_data/test_users',
        'clothing_data',
        'clothing_data/test_users',
        'clothing_data/auth_users'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"[INIT] Created directory: {directory}")
        else:
            print(f"[INIT] Directory exists: {directory}")

def check_required_files():
    """Check if required files exist"""
    required_files = [
        'firebase-service-account.json',
        'measurement_modules/__init__.py',
        'clothing_modules/__init__.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"[INIT] Required file exists: {file_path}")
    
    if missing_files:
        print(f"[INIT] WARNING: Missing required files: {missing_files}")
    else:
        print(f"[INIT] ✓ All required files present")

def start_workers():
    """Start background worker threads"""
    try:
        print(f"\n{'='*80}")
        print(f"[WORKERS] Starting background worker threads...")
        print(f"{'='*80}")
        
        # Start measurement worker
        print(f"[WORKERS] Starting measurement worker...")
        measurement_thread = start_measurement_worker()
        print(f"[WORKERS] ✓ Measurement worker started")
        
        # Start clothing worker
        print(f"[WORKERS] Starting clothing worker...")
        clothing_thread = start_clothing_worker()
        print(f"[WORKERS] ✓ Clothing worker started")
        
        print(f"[WORKERS] ✓ All workers started successfully")
        print(f"{'='*80}\n")
        
        return {
            'measurement_worker': measurement_thread,
            'clothing_worker': clothing_thread
        }
        
    except Exception as e:
        print(f"[WORKERS] ✗ Error starting workers: {str(e)}")
        print(f"[WORKERS] Traceback: {traceback.format_exc()}")
        return None

if __name__ == '__main__':
    print(f"\n{'='*100}")
    print(f"[APP STARTUP] Professional Measurement & Clothing Analysis API")
    print(f"[APP STARTUP] Version: 2.0.0")
    print(f"[APP STARTUP] Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*100}")
    
    try:
        # Initialize directories
        print(f"\n[INIT] Initializing application directories...")
        initialize_directories()
        
        # Check required files
        print(f"\n[INIT] Checking required files...")
        check_required_files()
        
        # Start background workers
        print(f"\n[INIT] Starting background workers...")
        workers = start_workers()
        
        if workers:
            print(f"\n[INIT] ✓ Application initialization completed successfully")
            
            # Display available endpoints
            print(f"\n[ENDPOINTS] Available API endpoints:")
            print(f"  • Body Measurements (Test): POST /api/measurements/test-process")
            print(f"  • Body Measurements (Auth): POST /api/measurements/auth-process")
            print(f"  • Clothing Measurements (Test): POST /api/clothing/test-measurement")
            print(f"  • Clothing Measurements (Auth): POST /api/clothing/auth-measurement")
            print(f"  • Web Scraping: POST /api/scraping/scrape")
            print(f"  • Health Check: GET /health")
            print(f"  • Queue Status: GET /api/queue/status")
            print(f"  • Auth Verification: POST /api/auth/verify")
            
            print(f"\n[FEATURES] System capabilities:")
            print(f"  ✓ Professional body measurements with VTON optimization")
            print(f"  ✓ Clothing measurement and size recommendation")
            print(f"  ✓ Google Vision API integration (firebase-service-account.json)")
            print(f"  ✓ Forbidden item filtering (underwear, electronics, etc.)")
            print(f"  ✓ Firebase authentication and Firestore storage")
            print(f"  ✓ Real-time job processing with queue system")
            print(f"  ✓ Professional sizing: S/M/L/XL/XXL (NO XS)")
            print(f"  ✓ Hardcoded inseam data from professional standards")
            
            print(f"\n[SERVER] Starting Flask development server...")
            print(f"[SERVER] Host: 127.0.0.1")
            print(f"[SERVER] Port: 5000")
            print(f"[SERVER] Debug: False (as requested)")
            print(f"[SERVER] Reloader: False")
            print(f"{'='*100}\n")
            
            # Start Flask app (debug=False as requested)
            app.run(
                host='127.0.0.1', 
                port=5000, 
                debug=False,  # Set to False as you requested
                use_reloader=False,
                threaded=True
            )
        else:
            print(f"\n[INIT] ✗ Failed to start workers, exiting...")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n[SHUTDOWN] Received keyboard interrupt, shutting down gracefully...")
        print(f"[SHUTDOWN] Application stopped at: {datetime.now().isoformat()}")
    except Exception as e:
        print(f"\n[STARTUP ERROR] Failed to start application: {str(e)}")
        print(f"[STARTUP ERROR] Traceback: {traceback.format_exc()}")
        sys.exit(1)
