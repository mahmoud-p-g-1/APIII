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
            'endpoints': {
                'scraping': '/api/scraping',
                'measurements': '/api/measurements',
                'vton': '/api/vton (coming soon)',
                'avatar': '/api/avatar (coming soon)'
            }
        }), 200
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }), 200
    
    # API documentation endpoint
    @app.route('/api')
    def api_docs():
        return jsonify({
            'service': 'FitMatch API',
            'version': '1.0.0',
            'endpoints': {
                'scraping': {
                    'base': '/api/scraping',
                    'routes': [
                        {
                            'method': 'POST',
                            'path': '/scrape',
                            'description': 'Scrape product with auth',
                            'requires_auth': True
                        },
                        {
                            'method': 'POST',
                            'path': '/test-scrape',
                            'description': 'Test scraping without auth',
                            'requires_auth': False
                        },
                        {
                            'method': 'GET',
                            'path': '/job/<job_id>',
                            'description': 'Get job status',
                            'requires_auth': True
                        },
                        {
                            'method': 'GET',
                            'path': '/test-job/<job_id>',
                            'description': 'Get test job status',
                            'requires_auth': False
                        },
                        {
                            'method': 'GET',
                            'path': '/my-imports',
                            'description': 'Get user imports',
                            'requires_auth': True
                        },
                        {
                            'method': 'GET',
                            'path': '/health',
                            'description': 'Health check',
                            'requires_auth': False
                        }
                    ]
                },
                'measurements': {
                    'base': '/api/measurements',
                    'routes': [
                        {
                            'method': 'POST',
                            'path': '/process',
                            'description': 'Process body measurements from images',
                            'requires_auth': False,
                            'body': {
                                'user_id': 'string (optional, default: anonymous)',
                                'front_image': 'base64 encoded image (required)',
                                'side_image': 'base64 encoded image (required)',
                                'manual_height': 'number in cm (optional, default: 170)',
                                'use_automatic_height': 'boolean (optional, default: true)'
                            }
                        },
                        {
                            'method': 'GET',
                            'path': '/status/<job_id>',
                            'description': 'Get measurement job status',
                            'requires_auth': False
                        },
                        {
                            'method': 'GET',
                            'path': '/results/<job_id>',
                            'description': 'Get measurement results',
                            'requires_auth': False
                        },
                        {
                            'method': 'GET',
                            'path': '/history/<user_id>',
                            'description': 'Get measurement history for user',
                            'requires_auth': False
                        }
                    ]
                }
            }
        }), 200
    
    # Measurements API info endpoint
    @app.route('/api/measurements')
    def measurements_info():
        return jsonify({
            'service': 'Body Measurements API',
            'version': '1.0.0',
            'description': 'Process body measurements from front and side images',
            'endpoints': [
                {
                    'method': 'POST',
                    'path': '/api/measurements/process',
                    'description': 'Submit images for measurement processing',
                    'example_request': {
                        'user_id': 'user123',
                        'front_image': 'base64_encoded_image_data',
                        'side_image': 'base64_encoded_image_data',
                        'manual_height': 170,
                        'use_automatic_height': True
                    },
                    'example_response': {
                        'job_id': 'uuid-string',
                        'status': 'pending',
                        'message': 'Measurement processing started'
                    }
                },
                {
                    'method': 'GET',
                    'path': '/api/measurements/status/<job_id>',
                    'description': 'Check processing status'
                },
                {
                    'method': 'GET',
                    'path': '/api/measurements/results/<job_id>',
                    'description': 'Get measurement results when completed'
                },
                {
                    'method': 'GET',
                    'path': '/api/measurements/history/<user_id>',
                    'description': 'Get user measurement history'
                }
            ],
            'test_with_curl': {
                'description': 'Test the API with curl',
                'command': '''curl -X POST http://localhost:5000/api/measurements/process \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "test", "front_image": "base64_image", "side_image": "base64_image"}'
                '''
            }
        }), 200
    
    return app

def register_blueprints(app):
    """Register all API blueprints"""
    
    # Import and register scraping blueprint
    try:
        from api.scraping import scraping_bp
        app.register_blueprint(scraping_bp, url_prefix='/api/scraping')
        print("✓ Registered Scraping API blueprint at /api/scraping")
    except ImportError as e:
        print(f"✗ Failed to register Scraping API: {e}")
    except Exception as e:
        print(f"✗ Error registering Scraping API: {e}")
    
    # Import and register measurements blueprint
    try:
        from api.measurements import measurements_bp
        app.register_blueprint(measurements_bp, url_prefix='/api/measurements')
        print("✓ Registered Measurements API blueprint at /api/measurements")
    except ImportError as e:
        print(f"✗ Failed to register Measurements API: {e}")
        print("  Make sure api/measurements/__init__.py and routes.py exist")
    except Exception as e:
        print(f"✗ Error registering Measurements API: {e}")
    
    # Future blueprints can be added here:
    # try:
    #     from api.vton import vton_bp
    #     app.register_blueprint(vton_bp, url_prefix='/api/vton')
    #     print("✓ Registered VTON API blueprint at /api/vton")
    # except ImportError:
    #     print("✗ VTON API not available yet")
    
    # try:
    #     from api.avatar import avatar_bp
    #     app.register_blueprint(avatar_bp, url_prefix='/api/avatar')
    #     print("✓ Registered Avatar API blueprint at /api/avatar")
    # except ImportError:
    #     print("✗ Avatar API not available yet")

# Create app instance
app = create_app()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Starting FitMatch API Server")
    print("="*60)
    
    # Import and start worker threads
    try:
        from workers.tasks import start_worker_threads
        start_worker_threads()
        print("✓ Scraping worker threads started")
    except ImportError:
        print("✗ Scraping workers not found")
    except Exception as e:
        print(f"✗ Error starting scraping workers: {e}")
    
    # Start measurement worker thread
    try:
        from workers.measurement_worker import start_measurement_worker
        start_measurement_worker()
        print("✓ Measurement worker thread started")
    except ImportError:
        print("✗ Measurement worker not found - create workers/measurement_worker.py")
    except Exception as e:
        print(f"✗ Error starting measurement worker: {e}")
    
    print("-"*60)
    print(f"Server running on http://{Config.HOST}:{Config.PORT}")
    print(f"API Documentation: http://{Config.HOST}:{Config.PORT}/api")
    print(f"Measurements API: http://{Config.HOST}:{Config.PORT}/api/measurements")
    print("="*60 + "\n")
    
    # Run Flask app
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
