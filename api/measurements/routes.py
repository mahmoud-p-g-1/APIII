# api/measurements/routes.py

from flask import Blueprint, request, jsonify
import os
import tempfile
import uuid
from datetime import datetime
import base64
import traceback
import sys
import shutil
import json

# Add measurement modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'measurement_modules'))

from firebase_config import get_access_token
from queue_manager import queue_manager

measurements_bp = Blueprint('measurements', __name__)

FIREBASE_PROJECT_ID = "fitmatch-1"

@measurements_bp.route('/process', methods=['POST'])
def process_measurements():
    """
    Process body measurements from front and side images
    Expected JSON:
    {
        "user_id": "string",
        "front_image": "base64_encoded_image",
        "side_image": "base64_encoded_image",
        "manual_height": 170,
        "use_automatic_height": true
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'front_image' not in data or 'side_image' not in data:
            return jsonify({
                'error': 'Missing required fields: front_image and side_image'
            }), 400
        
        user_id = data.get('user_id', 'anonymous')
        job_id = str(uuid.uuid4())
        
        # Create user-specific directory
        user_dir = os.path.join('measurement_data', user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Create job-specific directory
        job_dir = os.path.join(user_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        try:
            # Decode and save images
            front_image_data = base64.b64decode(data['front_image'])
            side_image_data = base64.b64decode(data['side_image'])
            
            front_image_path = os.path.join(job_dir, 'front.jpg')
            side_image_path = os.path.join(job_dir, 'side.jpg')
            
            with open(front_image_path, 'wb') as f:
                f.write(front_image_data)
            with open(side_image_path, 'wb') as f:
                f.write(side_image_data)
            
            # Save initial job status to Firestore
            save_measurement_job(job_id, user_id, 'pending', {
                'manual_height': data.get('manual_height', 170),
                'use_automatic_height': data.get('use_automatic_height', True)
            })
            
            # Add job to queue
            job_data = {
                'job_id': job_id,
                'user_id': user_id,
                'type': 'measurement',
                'front_image': front_image_path,
                'side_image': side_image_path,
                'manual_height': data.get('manual_height', 170),
                'use_automatic_height': data.get('use_automatic_height', True),
                'job_dir': job_dir
            }
            
            queue_manager.add_job(job_data)
            
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

@measurements_bp.route('/status/<job_id>', methods=['GET'])
def get_measurement_status(job_id):
    """Get the status of a measurement job"""
    try:
        job_data = get_measurement_job(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify({
            'job_id': job_data.get('job_id'),
            'status': job_data.get('status'),
            'created_at': job_data.get('created_at'),
            'error': job_data.get('error')
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@measurements_bp.route('/results/<job_id>', methods=['GET'])
def get_measurement_results(job_id):
    """Get the measurement results for a completed job"""
    try:
        job_data = get_measurement_job(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        
        if job_data.get('status') != 'completed':
            return jsonify({
                'error': 'Job not completed',
                'status': job_data.get('status')
            }), 400
        
        return jsonify({
            'job_id': job_id,
            'user_id': job_data.get('user_id'),
            'measurements': job_data.get('measurements'),
            'confidence_scores': job_data.get('confidence_scores'),
            'overall_confidence': job_data.get('overall_confidence'),
            'height_detection_method': job_data.get('height_detection_method'),
            'detected_height': job_data.get('detected_height'),
            'completed_at': job_data.get('completed_at'),
            'processed_images': job_data.get('processed_images', {})
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@measurements_bp.route('/history/<user_id>', methods=['GET'])
def get_measurement_history(user_id):
    """Get measurement history for a user"""
    try:
        token = get_access_token()
        if not token:
            return jsonify({'error': 'Firebase not initialized'}), 500
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Query user's measurements
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}/measurements"
        
        response = requests.get(url, headers=headers)
        
        measurements = []
        if response.status_code == 200:
            data = response.json()
            if 'documents' in data:
                for doc in data['documents']:
                    measurement_data = parse_firestore_document(doc)
                    measurements.append(measurement_data)
        
        return jsonify({
            'user_id': user_id,
            'measurements': measurements,
            'count': len(measurements)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def save_measurement_job(job_id, user_id, status, data=None):
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
        
        # Also save to user's subcollection
        if response.status_code in [200, 201]:
            user_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}/measurements/{job_id}"
            requests.patch(user_url, json=job_data, headers=headers)
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        print(f"Error saving measurement job: {e}")
        return False

def get_measurement_job(job_id):
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

def parse_firestore_document(doc):
    """Parse Firestore document to Python dict"""
    result = {}
    if 'fields' in doc:
        for key, value in doc['fields'].items():
            if 'stringValue' in value:
                # Check if it's JSON
                if key in ['measurements', 'confidence_scores', 'processed_images']:
                    try:
                        result[key] = json.loads(value['stringValue'])
                    except:
                        result[key] = value['stringValue']
                else:
                    result[key] = value['stringValue']
            elif 'doubleValue' in value:
                result[key] = value['doubleValue']
            elif 'integerValue' in value:
                result[key] = int(value['integerValue'])
            elif 'booleanValue' in value:
                result[key] = value['booleanValue']
    return result

# Add missing import
import requests
