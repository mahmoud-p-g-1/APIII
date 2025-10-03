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
import tempfile
from PIL import Image
import io
from urllib.parse import urlparse

clothing_bp = Blueprint('clothing', __name__)

FIREBASE_PROJECT_ID = "fitmatch-1"

# Allowed domains for image URLs
ALLOWED_DOMAINS = [
    'amazon.com', 'www.amazon.com', 'images-na.ssl-images-amazon.com', 'm.media-amazon.com',
    'ebay.com', 'www.ebay.com', 'i.ebayimg.com', 'p.turbosquid.com',
    'aliexpress.com', 'www.aliexpress.com', 'ae01.alicdn.com', 'ae04.alicdn.com',
    'alibaba.com', 'www.alibaba.com', 's.alicdn.com', 'sc04.alicdn.com',
    'hm.com', 'www2.hm.com', 'lp2.hm.com', 'image.hm.com'
]

@clothing_bp.route('/store_image', methods=['POST'])
def clothing_image_upload():
    """Upload clothing image from code/base64 or URL (Amazon, eBay, AliExpress, Alibaba, H&M only) using multipart/form-data"""
    try:
        print(f"\n{'='*80}")
        print(f"[CLOTHING IMAGE API] Clothing image upload request")
        print(f"[CLOTHING IMAGE API] Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*80}")
        
        # Check authentication (optional)
        auth_header = request.headers.get('Authorization')
        user_id = None
        is_authenticated = False
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_info = verify_token(token)
            if user_info:
                user_id = user_info.get('uid') or user_info.get('user_id', 'unknown_user')
                is_authenticated = True
                print(f"[CLOTHING IMAGE API] Authenticated user: {user_id}")
        
        if not is_authenticated:
            user_id = f"guest_{uuid.uuid4().hex[:8]}"
            print(f"[CLOTHING IMAGE API] Guest user: {user_id}")
        
        image_data = None
        image_source = None
        
        # Method 1: Base64 encoded image from form data
        if 'image_base64' in request.form:
            try:
                # Remove data URL prefix if present
                base64_data = request.form['image_base64']
                if base64_data.startswith('data:image'):
                    base64_data = base64_data.split(',')[1]
                
                # Decode base64
                import base64
                image_bytes = base64.b64decode(base64_data)
                image_data = io.BytesIO(image_bytes)
                image_source = "base64_code"
                
                print(f"[CLOTHING IMAGE API] ✓ Base64 image decoded successfully")
                
            except Exception as e:
                return jsonify({'error': f'Invalid base64 image data: {str(e)}'}), 400
        
        # Method 2: URL from allowed domains
        elif 'image_url' in request.form:
            image_url = request.form['image_url']
            
            # Validate domain
            parsed_url = urlparse(image_url)
            domain = parsed_url.netloc.lower()
            
            # Check if domain is allowed
            is_allowed_domain = False
            for allowed_domain in ALLOWED_DOMAINS:
                if domain == allowed_domain or domain.endswith('.' + allowed_domain):
                    is_allowed_domain = True
                    break
            
            if not is_allowed_domain:
                return jsonify({
                    'error': 'URL domain not allowed',
                    'allowed_domains': ['Amazon.com', 'eBay.com', 'AliExpress.com', 'Alibaba.com', 'H&M.com'],
                    'provided_domain': domain
                }), 400
            
            try:
                # Download image from URL
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(image_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Validate content type
                content_type = response.headers.get('content-type', '').lower()
                if not content_type.startswith('image/'):
                    return jsonify({'error': 'URL does not point to an image'}), 400
                
                image_data = io.BytesIO(response.content)
                image_source = f"url_{domain}"
                
                print(f"[CLOTHING IMAGE API] ✓ Image downloaded from: {domain}")
                
            except requests.exceptions.RequestException as e:
                return jsonify({'error': f'Failed to download image: {str(e)}'}), 400
        
        else:
            return jsonify({'error': 'Either image_base64 or image_url must be provided'}), 400
        
        # Validate and process image
        try:
            # Open image with PIL to validate
            pil_image = Image.open(image_data)
            
            # Validate image dimensions
            width, height = pil_image.size
            if width < 100 or height < 100:
                return jsonify({'error': 'Image too small (minimum 100x100 pixels)'}), 400
            
            if width > 4000 or height > 4000:
                return jsonify({'error': 'Image too large (maximum 4000x4000 pixels)'}), 400
            
            # Convert to RGB if necessary
            if pil_image.mode in ('RGBA', 'P'):
                pil_image = pil_image.convert('RGB')
            
            print(f"[CLOTHING IMAGE API] ✓ Image validated: {width}x{height} pixels")
            
        except Exception as e:
            return jsonify({'error': f'Invalid image format: {str(e)}'}), 400
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create directory structure
        if is_authenticated:
            job_dir = os.path.join('clothing_data', 'auth_users', user_id, job_id)
        else:
            job_dir = os.path.join('clothing_data', 'guest_users', user_id, job_id)
        
        os.makedirs(job_dir, exist_ok=True)
        
        # Save image
        image_filename = f'clothing_image_{job_id}.jpg'
        image_path = os.path.join(job_dir, image_filename)
        
        # Save as JPEG
        pil_image.save(image_path, 'JPEG', quality=90)
        
        print(f"[CLOTHING IMAGE API] ✓ Image saved: {image_path}")
        
        # Get body measurements if provided (for authenticated users)
        body_measurements = None
        if is_authenticated and 'body_measurements' in request.form:
            try:
                body_measurements_str = request.form['body_measurements']
                body_measurements = json.loads(body_measurements_str)
                body_measurements['user_id'] = user_id
                print(f"[CLOTHING IMAGE API] ✓ Body measurements provided for comparison")
                
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid body measurements JSON format'}), 400
        
        # Create job data
        job_data = {
            'job_id': job_id,
            'user_id': user_id,
            'type': 'clothing_measurement_auth' if is_authenticated else 'clothing_measurement',
            'clothing_image': image_path,
            'job_dir': job_dir,
            'is_test': not is_authenticated,
            'image_source': image_source,
            'created_at': datetime.now().isoformat()
        }
        
        if body_measurements:
            job_data['body_measurements'] = body_measurements
        
        # Add to processing queue
        queue_manager.add_job(job_data)
        
        # Response
        response_data = {
            'status': 'queued',
            'job_id': job_id,
            'message': 'Clothing image uploaded and queued for measurement analysis',
            'image_source': image_source,
            'user_type': 'authenticated' if is_authenticated else 'guest',
            'has_body_comparison': body_measurements is not None,
            'image_dimensions': f"{width}x{height}",
            'allowed_domains': ['Amazon.com', 'eBay.com', 'AliExpress.com', 'Alibaba.com', 'H&M.com']
        }
        
        print(f"[CLOTHING IMAGE API] ✓ Job queued successfully: {job_id}")
        
        return jsonify(response_data), 202
        
    except Exception as e:
        print(f"[CLOTHING IMAGE API] ✗ Error: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

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
