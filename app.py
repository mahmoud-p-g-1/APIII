# app.py
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from firebase_config import initialize_firebase
from datetime import datetime

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialize Firebase
    firebase_initialized = initialize_firebase()
    
    # Register blueprints
    register_blueprints(app)
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'service': 'FitMatch API',
            'version': '1.0.0',
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'firebase': firebase_initialized,
        }), 200
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }), 200
    
    return app

def register_blueprints(app):
    """Register all API blueprints"""
    # Import and register scraping blueprint
    from api.scraping import scraping_bp
    app.register_blueprint(scraping_bp, url_prefix='/api/scraping')
    print("Registered Scraping API blueprint at /api/scraping")
    
    # Import and register measurements blueprint - THIS WAS MISSING!
    from api.measurements import measurements_bp
    app.register_blueprint(measurements_bp, url_prefix='/api/measurements')
    print("Registered Measurements API blueprint at /api/measurements")

# Create app instance
app = create_app()

if __name__ == '__main__':
    # Start worker threads for scraping
    from workers.tasks import start_worker_threads
    start_worker_threads()
    print("Worker threads started")
    
    # Start measurement worker - THIS WAS MISSING!
    from workers.measurement_worker import start_measurement_worker
    start_measurement_worker()
    print("Measurement worker started")
    
    # Run Flask app
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
