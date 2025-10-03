# api/scraping/routes.py
from flask import Blueprint, request, jsonify
from firebase_config import get_scraped_data_from_firestore, require_auth, save_job_to_firestore, get_job_from_firestore, get_user_imports
from security import validate_url_security, detect_platform
from queue_manager import queue_manager
from utils.rate_limiter import check_rate_limit
import uuid
from datetime import datetime

# Create the blueprint with name 'scraping'
scraping_bp = Blueprint('scraping', __name__)

@scraping_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - NO RATE LIMIT"""
    return jsonify({
        'status': 'healthy',
        'service': 'Scraping API',
        'timestamp': datetime.now().isoformat(),
        'queue_size': queue_manager.get_queue_size()
    }), 200

@scraping_bp.route('/scrape', methods=['POST'])
@require_auth
def scrape_with_auth():
    """Main scraping endpoint with authentication - GENEROUS RATE LIMIT"""
    try:
        # Very generous rate limiting: 100 requests per minute
        user_id = request.user['uid']
        if not check_rate_limit(user_id, 'scrape', 100, 1):
            return jsonify({'error': 'Rate limit exceeded (100 requests per minute)'}), 429
        
        # Accept both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            # Form data
            data = request.form.to_dict()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url']
        
        # Security validation
        is_valid, message = validate_url_security(url)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Detect platform
        platform = detect_platform(url)
        if not platform:
            return jsonify({'error': 'Unsupported URL Format'}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        job_data = {
            'job_id': job_id,
            'user_id': user_id,
            'url': url,
            'platform': platform,
            'type': 'scraping',
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Save to Firestore
        save_job_to_firestore(user_id, job_data)
        
        # Add to queue
        if not queue_manager.add_job(job_data):
            return jsonify({'error': 'Queue is full, please try again later'}), 503
        
        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'Scraping job queued successfully'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scraping_bp.route('/test-scrape', methods=['POST'])
def test_scrape():
    """Test endpoint without authentication - NO RATE LIMIT - ACCEPTS FORM DATA"""
    try:
        # Accept both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            # Form data (this is what HTTPie GUI sends with form body type)
            data = request.form.to_dict()
        
        # If still no data, try to get it from request.values
        if not data:
            data = request.values.to_dict()
        
        if not data or 'url' not in data:
            return jsonify({
                'error': 'URL is required',
                'hint': 'Send as form data with key "url" or as JSON {"url": "..."}'
            }), 400
        
        url = data['url']
        
        # Security validation
        is_valid, message = validate_url_security(url)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Detect platform
        platform = detect_platform(url)
        if not platform:
            return jsonify({'error': 'Unsupported URL Format'}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        job_data = {
            'job_id': job_id,
            'user_id': 'test_user',
            'url': url,
            'platform': platform,
            'type': 'scraping',
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Save to Firestore
        save_job_to_firestore('test_user', job_data)
        
        # Add to queue
        if not queue_manager.add_job(job_data):
            return jsonify({'error': 'Queue is full, please try again later'}), 503
        
        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'Test scraping job queued successfully',
            'note': 'This is a test endpoint for development'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scraping_bp.route('/job/<job_id>', methods=['GET'])
@require_auth
def get_job_status(job_id):
    """Get job status with results if completed - NO RATE LIMIT"""
    try:
        user_id = request.user['uid']
        job_data = get_job_from_firestore(user_id, job_id)
        
        if job_data:
            # If job is completed, try to get the scraped results
            if job_data.get('status') == 'completed' and 'importId' in job_data:
                try:
                    # Get the actual scraped data from Firestore
                    import_id = job_data['importId']
                    scraped_data = get_scraped_data_from_firestore(user_id, import_id)
                    
                    if scraped_data:
                        # Add the scraped results to the job response
                        job_data['results'] = {
                            'platform': scraped_data.get('retailer', job_data.get('platform')),
                            'name': scraped_data.get('name', 'Unknown Product'),
                            'images': scraped_data.get('imageUrls', []),
                            'import_id': import_id,
                            'product_url': scraped_data.get('productUrl', job_data.get('url')),
                            'created_at': scraped_data.get('createdAt'),
                            'scraped_successfully': True
                        }
                        
                        # Add individual image URLs for easy access
                        for i in range(1, 6):
                            img_key = f'imageUrl{i}'
                            if img_key in scraped_data:
                                job_data['results'][f'image_{i}'] = scraped_data[img_key]
                
                except Exception as e:
                    print(f"Error getting scraped results: {str(e)}")
                    # Still return job data even if we can't get results
            
            return jsonify(job_data), 200
        else:
            return jsonify({'error': 'Job not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scraping_bp.route('/test-job/<job_id>', methods=['GET'])
def get_test_job_status(job_id):
    """Get test job status without authentication - NO RATE LIMIT"""
    try:
        job_data = get_job_from_firestore('test_user', job_id)
        
        if job_data:
            # If job is completed, try to get the scraped results
            if job_data.get('status') == 'completed' and 'importId' in job_data:
                try:
                    # Get the actual scraped data from Firestore
                    import_id = job_data['importId']
                    scraped_data = get_scraped_data_from_firestore('test_user', import_id)
                    
                    if scraped_data:
                        # Add the scraped results to the job response
                        job_data['results'] = {
                            'platform': scraped_data.get('retailer', job_data.get('platform')),
                            'name': scraped_data.get('name', 'Unknown Product'),
                            'images': scraped_data.get('imageUrls', []),
                            'import_id': import_id,
                            'product_url': scraped_data.get('productUrl', job_data.get('url')),
                            'created_at': scraped_data.get('createdAt'),
                            'scraped_successfully': True
                        }
                        
                        # Add individual image URLs for easy access
                        for i in range(1, 6):
                            img_key = f'imageUrl{i}'
                            if img_key in scraped_data:
                                job_data['results'][f'image_{i}'] = scraped_data[img_key]
                
                except Exception as e:
                    print(f"Error getting scraped results: {str(e)}")
                    # Still return job data even if we can't get results
            
            return jsonify(job_data), 200
        else:
            return jsonify({'error': 'Job not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@scraping_bp.route('/my-imports', methods=['GET'])
@require_auth
def get_my_imports():
    """Get user's URL imports from Firestore"""
    try:
        user_id = request.user['uid']
        limit = request.args.get('limit', 10, type=int)
        
        imports = get_user_imports(user_id, limit)
        
        return jsonify({
            'imports': imports,
            'count': len(imports)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
