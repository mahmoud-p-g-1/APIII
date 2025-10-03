# api/clothing/routes.py

from flask import Blueprint, request, jsonify
import os
import uuid
import traceback
from datetime import datetime
from werkzeug.utils import secure_filename
from firebase_config import verify_token, get_access_token
from queue_manager import queue_manager
import json
import requests

clothing_bp = Blueprint('clothing', __name__)

FIREBASE_PROJECT_ID = "fitmatch-1"

@clothing_bp.route('/test-measurement', methods=['POST'])
def test_clothing_measurement():
    """Test endpoint for clothing measurement (no auth required)"""
    try:
        print(f"\n{'='*80}")
        print(f"[CLOTHING TEST API] Test clothing measurement request")
        print(f"[CLOTHING TEST API] Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*80}")
        
        # Check if file is uploaded
        if 'clothing_image' not in request.files:
            return jsonify({'error': 'No clothing image uploaded'}), 400
        
        clothing_file = request.files['clothing_image']
        if clothing_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Generate job ID (following your pattern)
        job_id = str(uuid.uuid4())
        test_user_id = f"test_clothing_{uuid.uuid4().hex[:8]}"
        
        print(f"[CLOTHING TEST API] Job ID: {job_id}")
        print(f"[CLOTHING TEST API] Test User ID: {test_user_id}")
        
        # Create directory structure (following your measurement_data pattern)
        test_dir = os.path.join('clothing_data', 'test_users', test_user_id, job_id)
        os.makedirs(test_dir, exist_ok=True)
        
        # Save clothing image
        filename = secure_filename(clothing_file.filename)
        clothing_image_path = os.path.join(test_dir, f'clothing_{filename}')
        clothing_file.save(clothing_image_path)
        
        print(f"[CLOTHING TEST API] Saved: {clothing_image_path}")
        
        # Create job data (following your measurement job pattern)
        job_data = {
            'job_id': job_id,
            'user_id': test_user_id,
            'type': 'clothing_measurement',
            'clothing_image': clothing_image_path,
            'job_dir': test_dir,
            'is_test': True,
            'created_at': datetime.now().isoformat()
        }
        
        # Add to queue (using your existing queue_manager)
        queue_manager.add_job(job_data)
        
        return jsonify({
            'status': 'queued',
            'job_id': job_id,
            'message': 'Clothing measurement job queued for processing',
            'test_mode': True
        }), 202
        
    except Exception as e:
        print(f"[CLOTHING TEST API] ✗ Error: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@clothing_bp.route('/auth-measurement', methods=['POST'])
def auth_clothing_measurement():
    """Authenticated endpoint for clothing measurement with body comparison"""
    try:
        print(f"\n{'='*80}")
        print(f"[CLOTHING AUTH API] Authenticated clothing measurement request")
        print(f"[CLOTHING AUTH API] Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*80}")
        
        # Verify authentication (using your existing auth system)
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        user_info = verify_token(token)
        if not user_info:
            return jsonify({'error': 'Invalid authentication token'}), 401
        
        user_id = user_info.get('uid') or user_info.get('user_id', 'unknown_user')
        print(f"[CLOTHING AUTH API] Authenticated user: {user_id}")
        
        # Check for clothing image
        if 'clothing_image' not in request.files:
            return jsonify({'error': 'No clothing image uploaded'}), 400
        
        clothing_file = request.files['clothing_image']
        if clothing_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get body measurements for comparison (required for auth endpoint)
        body_measurements = request.form.get('body_measurements')
        if not body_measurements:
            return jsonify({'error': 'Body measurements required for size recommendation'}), 400
        
        try:
            body_measurements = json.loads(body_measurements)
            # FIXED: Add user_id to body measurements for proper user detection
            body_measurements['user_id'] = user_id
            print(f"[CLOTHING AUTH API] Body measurements loaded for comparison")
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid body measurements JSON format'}), 400
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create directory (following your auth pattern)
        auth_dir = os.path.join('clothing_data', 'auth_users', user_id, job_id)
        os.makedirs(auth_dir, exist_ok=True)
        
        # Save clothing image
        filename = secure_filename(clothing_file.filename)
        clothing_image_path = os.path.join(auth_dir, f'clothing_{filename}')
        clothing_file.save(clothing_image_path)
        
        print(f"[CLOTHING AUTH API] Saved: {clothing_image_path}")
        
        # Create job data
        job_data = {
            'job_id': job_id,
            'user_id': user_id,
            'type': 'clothing_measurement_auth',
            'clothing_image': clothing_image_path,
            'body_measurements': body_measurements,
            'job_dir': auth_dir,
            'is_test': False,
            'created_at': datetime.now().isoformat()
        }
        
        # Add to queue
        queue_manager.add_job(job_data)
        
        return jsonify({
            'status': 'queued',
            'job_id': job_id,
            'message': 'Clothing measurement job queued for processing',
            'has_body_comparison': True,
            'test_mode': False
        }), 202
        
    except Exception as e:
        print(f"[CLOTHING AUTH API] ✗ Error: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@clothing_bp.route('/status/<job_id>', methods=['GET'])
def get_clothing_status(job_id):
    """FIXED: Get clothing job status with proper completion detection"""
    try:
        print(f"[CLOTHING STATUS] Getting status for job: {job_id}")
        
        token = get_access_token()
        if not token:
            return jsonify({'error': 'Firebase not available'}), 503
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get job from clothing_jobs collection
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/clothing_jobs/{job_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            doc = response.json()
            if 'fields' in doc:
                # Extract status
                status = extract_firestore_value(doc['fields'].get('status', {'stringValue': 'unknown'}))
                
                print(f"[CLOTHING STATUS] Job {job_id} status: {status}")
                
                if status == 'completed':
                    # Return full results for completed jobs
                    result = {}
                    for key, value in doc['fields'].items():
                        result[key] = extract_firestore_value(value)
                    
                    # Parse JSON strings back to objects
                    if 'clothing_measurements' in result:
                        try:
                            result['clothing_measurements'] = json.loads(result['clothing_measurements'])
                        except:
                            pass
                    
                    if 'detailed_fit_analysis' in result:
                        try:
                            result['detailed_fit_analysis'] = json.loads(result['detailed_fit_analysis'])
                        except:
                            pass
                    
                    if 'error_corrections' in result:
                        try:
                            result['error_corrections'] = json.loads(result['error_corrections'])
                        except:
                            pass
                    
                    if 'reprocessing_history' in result:
                        try:
                            result['reprocessing_history'] = json.loads(result['reprocessing_history'])
                        except:
                            pass
                    
                    return jsonify(result), 200
                
                elif status == 'processing':
                    return jsonify({
                        'job_id': job_id,
                        'status': 'processing',
                        'message': 'Clothing measurement in progress'
                    }), 200
                
                elif status == 'failed':
                    error_msg = extract_firestore_value(doc['fields'].get('error', {'stringValue': 'Unknown error'}))
                    return jsonify({
                        'job_id': job_id,
                        'status': 'failed',
                        'error': error_msg
                    }), 200
                
                elif status == 'rejected':
                    rejection_reason = extract_firestore_value(doc['fields'].get('rejection_reason', {'stringValue': 'Unknown reason'}))
                    return jsonify({
                        'job_id': job_id,
                        'status': 'rejected',
                        'reason': rejection_reason
                    }), 200
                
                else:
                    return jsonify({
                        'job_id': job_id,
                        'status': status,
                        'message': f'Job status: {status}'
                    }), 200
        
        return jsonify({'error': 'Job not found'}), 404
        
    except Exception as e:
        print(f"[CLOTHING STATUS] Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@clothing_bp.route('/test-result/<job_id>', methods=['GET'])
def get_clothing_test_result(job_id):
    """FIXED: Get clothing test result (no auth required for test mode)"""
    try:
        print(f"[CLOTHING TEST RESULT] Getting test result for job: {job_id}")
        
        token = get_access_token()
        if not token:
            return jsonify({'error': 'Firebase not available'}), 503
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get job from clothing_jobs collection
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/clothing_jobs/{job_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            doc = response.json()
            if 'fields' in doc:
                # Convert Firestore format to regular dict
                result = {}
                for key, value in doc['fields'].items():
                    result[key] = extract_firestore_value(value)
                
                # Parse JSON strings back to objects
                if 'clothing_measurements' in result:
                    try:
                        result['clothing_measurements'] = json.loads(result['clothing_measurements'])
                    except:
                        pass
                
                if 'detailed_fit_analysis' in result:
                    try:
                        result['detailed_fit_analysis'] = json.loads(result['detailed_fit_analysis'])
                    except:
                        pass
                
                if 'error_corrections' in result:
                    try:
                        result['error_corrections'] = json.loads(result['error_corrections'])
                    except:
                        pass
                
                if 'reprocessing_history' in result:
                    try:
                        result['reprocessing_history'] = json.loads(result['reprocessing_history'])
                    except:
                        pass
                
                if 'vision_analysis' in result:
                    try:
                        result['vision_analysis'] = json.loads(result['vision_analysis'])
                    except:
                        pass
                
                return jsonify(result), 200
        
        return jsonify({'error': 'Test result not found'}), 404
        
    except Exception as e:
        print(f"[CLOTHING TEST RESULT] Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@clothing_bp.route('/result/<job_id>', methods=['GET'])
def get_clothing_result(job_id):
    """FIXED: Get clothing result for authenticated users"""
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        user_info = verify_token(token)
        if not user_info:
            return jsonify({'error': 'Invalid authentication token'}), 401
        
        user_id = user_info.get('uid') or user_info.get('user_id', 'unknown_user')
        print(f"[CLOTHING RESULT] Getting result for job: {job_id}, user: {user_id}")
        
        firebase_token = get_access_token()
        if not firebase_token:
            return jsonify({'error': 'Firebase not available'}), 503
        
        headers = {
            'Authorization': f'Bearer {firebase_token}',
            'Content-Type': 'application/json'
        }
        
        # Get job from clothing_jobs collection
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/clothing_jobs/{job_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            doc = response.json()
            if 'fields' in doc:
                # Convert Firestore format to regular dict
                result = {}
                for key, value in doc['fields'].items():
                    result[key] = extract_firestore_value(value)
                
                # Parse JSON strings back to objects
                if 'clothing_measurements' in result:
                    try:
                        result['clothing_measurements'] = json.loads(result['clothing_measurements'])
                    except:
                        pass
                
                if 'detailed_fit_analysis' in result:
                    try:
                        result['detailed_fit_analysis'] = json.loads(result['detailed_fit_analysis'])
                    except:
                        pass
                
                if 'error_corrections' in result:
                    try:
                        result['error_corrections'] = json.loads(result['error_corrections'])
                    except:
                        pass
                
                if 'reprocessing_history' in result:
                    try:
                        result['reprocessing_history'] = json.loads(result['reprocessing_history'])
                    except:
                        pass
                
                return jsonify(result), 200
        
        return jsonify({'error': 'Result not found'}), 404
        
    except Exception as e:
        print(f"[CLOTHING RESULT] Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def extract_firestore_value(firestore_value):
    """Extract Python value from Firestore format"""
    if 'stringValue' in firestore_value:
        return firestore_value['stringValue']
    elif 'integerValue' in firestore_value:
        return int(firestore_value['integerValue'])
    elif 'doubleValue' in firestore_value:
        return firestore_value['doubleValue']
    elif 'booleanValue' in firestore_value:
        return firestore_value['booleanValue']
    elif 'arrayValue' in firestore_value:
        values = []
        if 'values' in firestore_value['arrayValue']:
            for v in firestore_value['arrayValue']['values']:
                values.append(extract_firestore_value(v))
        return values
    elif 'mapValue' in firestore_value:
        result = {}
        if 'fields' in firestore_value['mapValue']:
            for key, value in firestore_value['mapValue']['fields'].items():
                result[key] = extract_firestore_value(value)
        return result
    elif 'nullValue' in firestore_value:
        return None
    else:
        return None
