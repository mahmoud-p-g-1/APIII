# api/measurements/routes.py

from flask import Blueprint, request, jsonify
import os
import tempfile
import uuid
from datetime import datetime
import traceback
import sys
import shutil
import json
from werkzeug.utils import secure_filename

# Add measurement modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'measurement_modules'))

from firebase_config import require_auth, get_access_token, extract_value
from queue_manager import queue_manager
from utils.rate_limiter import check_rate_limit
import requests

measurements_bp = Blueprint('measurements', __name__)

FIREBASE_PROJECT_ID = "fitmatch-1"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@measurements_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Measurements API',
        'timestamp': datetime.now().isoformat(),
        'queue_size': queue_manager.get_queue_size()
    }), 200

@measurements_bp.route('/process', methods=['POST'])
@require_auth
def process_measurements_auth():
    """
    Process body measurements with authentication
    Expects multipart/form-data with:
    - front_img: Image file
    - side_img: Image file
    - manual_height: Number (optional, default 170)
    - use_automatic_height: Boolean (optional, default true)
    """
    try:
        # Get authenticated user ID from Firebase token
        user_id = request.user.get('uid')
        
        # Rate limiting: 50 requests per minute
        if not check_rate_limit(user_id, 'measurements', 50, 1):
            return jsonify({'error': 'Rate limit exceeded (50 requests per minute)'}), 429
        
        # Check if files are present
        if 'front_img' not in request.files or 'side_img' not in request.files:
            return jsonify({
                'error': 'Missing required files: front_img and side_img',
                'hint': 'Send as multipart/form-data with files named front_img and side_img'
            }), 400
        
        front_file = request.files['front_img']
        side_file = request.files['side_img']
        
        # Validate files
        if front_file.filename == '' or side_file.filename == '':
            return jsonify({'error': 'No files selected'}), 400
        
        if not (allowed_file(front_file.filename) and allowed_file(side_file.filename)):
            return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, bmp'}), 400
        
        # Get optional parameters from form data
        manual_height = float(request.form.get('manual_height', 170))
        use_automatic_height = request.form.get('use_automatic_height', 'true').lower() == 'true'
        
        job_id = str(uuid.uuid4())
        
        # Create user-specific directory
        user_dir = os.path.join('measurement_data', user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Create job-specific directory
        job_dir = os.path.join(user_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        try:
            # Save uploaded files
            front_image_path = os.path.join(job_dir, f'front_{secure_filename(front_file.filename)}')
            side_image_path = os.path.join(job_dir, f'side_{secure_filename(side_file.filename)}')
            
            front_file.save(front_image_path)
            side_file.save(side_image_path)
            
            # Save initial job status to Firestore
            save_measurement_job_to_firestore(job_id, user_id, 'pending', {
                'manual_height': manual_height,
                'use_automatic_height': use_automatic_height,
                'authenticated': True,
                'test_mode': False
            })
            
            # Add job to queue
            job_data = {
                'job_id': job_id,
                'user_id': user_id,
                'type': 'measurement',
                'front_image': front_image_path,
                'side_image': side_image_path,
                'manual_height': manual_height,
                'use_automatic_height': use_automatic_height,
                'job_dir': job_dir,
                'authenticated': True
            }
            
            if not queue_manager.add_job(job_data):
                return jsonify({'error': 'Queue is full, please try again later'}), 503
            
            return jsonify({
                'job_id': job_id,
                'status': 'pending',
                'message': 'Measurement processing started',
                'user_id': user_id
            }), 202
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir, ignore_errors=True)
            raise e
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@measurements_bp.route('/test-process', methods=['POST'])
def process_measurements_test():
    """
    Test endpoint for measurements without authentication
    Expects multipart/form-data with:
    - front_img: Image file
    - side_img: Image file
    - manual_height: Number (optional, default 170)
    - use_automatic_height: Boolean (optional, default true)
    """
    try:
        # Use test user ID
        user_id = 'test_user_' + str(uuid.uuid4())[:8]
        
        # Check if files are present
        if 'front_img' not in request.files or 'side_img' not in request.files:
            return jsonify({
                'error': 'Missing required files: front_img and side_img',
                'hint': 'Send as multipart/form-data with files named front_img and side_img'
            }), 400
        
        front_file = request.files['front_img']
        side_file = request.files['side_img']
        
        # Validate files
        if front_file.filename == '' or side_file.filename == '':
            return jsonify({'error': 'No files selected'}), 400
        
        if not (allowed_file(front_file.filename) and allowed_file(side_file.filename)):
            return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, bmp'}), 400
        
        # Get optional parameters
        manual_height = float(request.form.get('manual_height', 170))
        use_automatic_height = request.form.get('use_automatic_height', 'true').lower() == 'true'
        
        job_id = str(uuid.uuid4())
        
        # Create test user directory
        user_dir = os.path.join('measurement_data', 'test_users', user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Create job directory
        job_dir = os.path.join(user_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        try:
            # Save uploaded files
            front_image_path = os.path.join(job_dir, f'front_{secure_filename(front_file.filename)}')
            side_image_path = os.path.join(job_dir, f'side_{secure_filename(side_file.filename)}')
            
            front_file.save(front_image_path)
            side_file.save(side_image_path)
            
            # Save job status - ALWAYS set test_mode to True for test jobs
            save_measurement_job_to_firestore(job_id, user_id, 'pending', {
                'manual_height': manual_height,
                'use_automatic_height': use_automatic_height,
                'authenticated': False,
                'test_mode': True  # This is critical for test endpoint access
            })
            
            # Add to queue
            job_data = {
                'job_id': job_id,
                'user_id': user_id,
                'type': 'measurement',
                'front_image': front_image_path,
                'side_image': side_image_path,
                'manual_height': manual_height,
                'use_automatic_height': use_automatic_height,
                'job_dir': job_dir,
                'authenticated': False,
                'test_mode': True
            }
            
            if not queue_manager.add_job(job_data):
                return jsonify({'error': 'Queue is full, please try again later'}), 503
            
            return jsonify({
                'job_id': job_id,
                'status': 'pending',
                'message': 'Test measurement processing started',
                'user_id': user_id,
                'note': 'This is a test endpoint. Results will be deleted after 24 hours.'
            }), 202
            
        except Exception as e:
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir, ignore_errors=True)
            raise e
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@measurements_bp.route('/test-status/<job_id>', methods=['GET'])
def get_measurement_status_test(job_id):
    """Get test measurement job status (no auth required)"""
    try:
        job_data = get_measurement_job_from_firestore(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        
        # Check if it's a test job - this is the fix for the 403 error
        # Accept jobs that are either marked as test_mode or from test_user
        is_test_job = job_data.get('test_mode', False) or job_data.get('user_id', '').startswith('test_user_')
        
        if not is_test_job:
            return jsonify({'error': 'This endpoint is only for test jobs'}), 403
        
        return jsonify({
            'job_id': job_data.get('job_id'),
            'status': job_data.get('status'),
            'created_at': job_data.get('created_at'),
            'error': job_data.get('error')
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@measurements_bp.route('/results/<job_id>', methods=['GET'])
@require_auth
def get_measurement_results_auth(job_id):
    """Get measurement results (authenticated)"""
    try:
        user_id = request.user.get('uid')
        print(f"[AUTH DEBUG] Token user_id: {user_id}")
        
        job_data = get_measurement_job_from_firestore(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        
        print(f"[AUTH DEBUG] Job user_id: {job_data.get('user_id')}")
        print(f"[AUTH DEBUG] All job keys: {list(job_data.keys())}")
        
        # Check if job belongs to user OR if it's a test job
        job_user_id = job_data.get('user_id')
        is_test_job = job_data.get('test_mode', False)
        
        if job_user_id != user_id and not is_test_job:
            return jsonify({
                'error': 'Unauthorized',
                'debug_info': {
                    'token_user_id': user_id,
                    'job_user_id': job_user_id,
                    'is_test_job': is_test_job,
                    'match': job_user_id == user_id
                }
            }), 403
        
        if job_data.get('status') != 'completed':
            return jsonify({
                'error': 'Job not completed',
                'status': job_data.get('status')
            }), 400
        
        return jsonify({
            'job_id': job_id,
            'measurements': job_data.get('measurements'),
            'confidence_scores': job_data.get('confidence_scores'),
            'overall_confidence': job_data.get('overall_confidence'),
            'height_detection_method': job_data.get('height_detection_method'),
            'detected_height': job_data.get('detected_height'),
            'completed_at': job_data.get('completed_at'),
            'image_quality_issues': job_data.get('image_quality_issues', {}),
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@measurements_bp.route('/status/<job_id>', methods=['GET'])
@require_auth
def get_measurement_status_auth(job_id):
    """Get measurement job status (authenticated)"""
    try:
        user_id = request.user.get('uid')
        print(f"[AUTH DEBUG] Token user_id: {user_id}")
        
        job_data = get_measurement_job_from_firestore(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        
        print(f"[AUTH DEBUG] Job user_id: {job_data.get('user_id')}")
        
        # Check if job belongs to user OR if it's a test job
        job_user_id = job_data.get('user_id')
        is_test_job = job_data.get('test_mode', False)
        
        if job_user_id != user_id and not is_test_job:
            return jsonify({
                'error': 'Unauthorized',
                'debug_info': {
                    'token_user_id': user_id,
                    'job_user_id': job_user_id,
                    'is_test_job': is_test_job
                }
            }), 403
        
        return jsonify({
            'job_id': job_data.get('job_id'),
            'status': job_data.get('status'),
            'created_at': job_data.get('created_at'),
            'error': job_data.get('error'),
            'image_quality_issues': job_data.get('image_quality_issues', []),
            'processing_warnings': job_data.get('processing_warnings', [])
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@measurements_bp.route('/test-results/<job_id>', methods=['GET'])
def get_measurement_results_test(job_id):
    """Get test measurement results (no auth required)"""
    try:
        job_data = get_measurement_job_from_firestore(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        
        # Check if it's a test job - accept both test_mode flag and test_user prefix
        is_test_job = job_data.get('test_mode', False) or job_data.get('user_id', '').startswith('test_user_')
        
        if not is_test_job:
            return jsonify({'error': 'This endpoint is only for test jobs'}), 403
        
        if job_data.get('status') != 'completed':
            return jsonify({
                'error': 'Job not completed',
                'status': job_data.get('status')
            }), 400
        
        return jsonify({
            'job_id': job_id,
            'measurements': job_data.get('measurements'),
            'confidence_scores': job_data.get('confidence_scores'),
            'overall_confidence': job_data.get('overall_confidence'),
            'height_detection_method': job_data.get('height_detection_method'),
            'detected_height': job_data.get('detected_height'),
            'completed_at': job_data.get('completed_at')
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@measurements_bp.route('/history', methods=['GET'])
@require_auth
def get_measurement_history_auth():
    """Get authenticated user's measurement history"""
    try:
        user_id = request.user.get('uid')
        limit = request.args.get('limit', 10, type=int)
        
        measurements = get_user_measurements_from_firestore(user_id, limit)
        
        return jsonify({
            'user_id': user_id,
            'measurements': measurements,
            'count': len(measurements)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@measurements_bp.route('/compare', methods=['POST'])
@require_auth
def compare_measurements_auth():
    """Compare two measurement sets (authenticated)"""
    try:
        user_id = request.user.get('uid')
        data = request.get_json()
        
        job_id_1 = data.get('job_id_1')
        job_id_2 = data.get('job_id_2')
        
        if not job_id_1 or not job_id_2:
            return jsonify({'error': 'Two job IDs required'}), 400
        
        # Get both measurements
        job1 = get_measurement_job_from_firestore(job_id_1)
        job2 = get_measurement_job_from_firestore(job_id_2)
        
        if not job1 or not job2:
            return jsonify({'error': 'One or both jobs not found'}), 404
        
        # Verify both jobs belong to user
        if job1.get('user_id') != user_id or job2.get('user_id') != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        measurements1 = job1.get('measurements', {})
        measurements2 = job2.get('measurements', {})
        
        # Calculate differences
        comparison = {}
        for key in measurements1:
            if key in measurements2:
                if isinstance(measurements1[key], (int, float)) and isinstance(measurements2[key], (int, float)):
                    diff = measurements2[key] - measurements1[key]
                    percentage = (diff / measurements1[key]) * 100 if measurements1[key] != 0 else 0
                    comparison[key] = {
                        'measurement_1': measurements1[key],
                        'measurement_2': measurements2[key],
                        'difference': diff,
                        'percentage_change': percentage
                    }
        
        return jsonify({
            'job_id_1': job_id_1,
            'job_id_2': job_id_2,
            'comparison': comparison,
            'date_1': job1.get('completed_at'),
            'date_2': job2.get('completed_at')
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Firestore helper functions
def save_measurement_job_to_firestore(job_id, user_id, status, data=None):
    """Save measurement job to Firestore"""
    try:
        token = get_access_token()
        if not token:
            print("No access token available")
            return False
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        job_data = {
            'fields': {
                'job_id': {'stringValue': job_id},
                'user_id': {'stringValue': user_id},
                'status': {'stringValue': status},
                'created_at': {'stringValue': datetime.now().isoformat()},
                'type': {'stringValue': 'measurement'}
            }
        }
        
        # ALWAYS set test_mode for test users
        is_test = user_id.startswith('test_user_')
        if is_test:
            job_data['fields']['test_mode'] = {'booleanValue': True}
        
        if data:
            for key, value in data.items():
                if isinstance(value, str):
                    job_data['fields'][key] = {'stringValue': value}
                elif isinstance(value, bool):
                    job_data['fields'][key] = {'booleanValue': value}
                elif isinstance(value, (int, float)):
                    job_data['fields'][key] = {'doubleValue': float(value)}
                elif isinstance(value, dict):
                    job_data['fields'][key] = {'stringValue': json.dumps(value)}
        
        # Save to main collection
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/measurement_jobs/{job_id}"
        response = requests.patch(url, json=job_data, headers=headers)
        
        print(f"Firestore save response: {response.status_code}")
        if response.status_code not in [200, 201]:
            print(f"Firestore error: {response.text}")
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        print(f"Error saving measurement job: {e}")
        return False


def get_measurement_job_from_firestore(job_id):
    """Get measurement job from Firestore"""
    try:
        token = get_access_token()
        if not token:
            return None
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/measurement_jobs/{job_id}"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return parse_firestore_document(response.json())
        
        return None
        
    except Exception as e:
        print(f"Error getting measurement job: {e}")
        return None

def get_user_measurements_from_firestore(user_id, limit=10):
    """Get user's measurements from Firestore"""
    try:
        token = get_access_token()
        if not token:
            return []
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}/measurements"
        
        response = requests.get(url, headers=headers)
        
        measurements = []
        if response.status_code == 200:
            data = response.json()
            if 'documents' in data:
                for doc in data['documents']:
                    measurement_data = parse_firestore_document(doc)
                    measurements.append(measurement_data)
        
        # Sort by created_at and limit
        measurements.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return measurements[:limit]
        
    except Exception as e:
        print(f"Error getting user measurements: {e}")
        return []

def parse_firestore_document(doc):
    """Parse Firestore document to Python dict"""
    from firebase_config import extract_value
    
    result = {}
    if 'fields' in doc:
        for key, value in doc['fields'].items():
            # Check if it's JSON string for complex objects
            if 'stringValue' in value and key in ['measurements', 'confidence_scores', 'processed_images']:
                try:
                    result[key] = json.loads(value['stringValue'])
                except:
                    result[key] = extract_value(value)
            else:
                result[key] = extract_value(value)
    return result

def update_measurement_job_status(job_id, user_id, status, result_data=None):
    """Update measurement job status in Firestore"""
    try:
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if result_data:
            update_data.update(result_data)
        
        return save_measurement_job_to_firestore(job_id, user_id, status, update_data)
        
    except Exception as e:
        print(f"Error updating measurement job: {e}")
        return False
