# api/scraping/logic.py
import uuid
from datetime import datetime
from security import validate_url_security, detect_platform
from queue_manager import queue_manager
from firebase_config import save_job_to_firestore, get_job_from_firestore

class ScrapingLogic:
    """Business logic for scraping operations"""
    
    def process_scraping_request(self, user_id, url, is_test=False):
        """Process a scraping request"""
        try:
            # Security validation
            is_valid, message = validate_url_security(url)
            if not is_valid:
                return {
                    'success': False,
                    'error': message,
                    'status_code': 400
                }
            
            # Detect platform
            platform = detect_platform(url)
            if not platform:
                return {
                    'success': False,
                    'error': 'Unsupported URL Format',
                    'status_code': 400
                }
            
            # Create job
            job_id = str(uuid.uuid4())
            job_data = {
                'job_id': job_id,
                'user_id': user_id,
                'url': url,
                'platform': platform,
                'type': 'scraping',
                'status': 'queued',
                'is_test': is_test,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save to storage
            save_job_to_firestore(user_id, job_data)
            
            # Add to queue
            if not queue_manager.add_job(job_data):
                return {
                    'success': False,
                    'error': 'Queue is full, please try again later',
                    'status_code': 503
                }
            
            return {
                'success': True,
                'data': {
                    'job_id': job_id,
                    'status': 'queued',
                    'message': 'Scraping job queued successfully',
                    'platform': platform
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': 500
            }
    
    def get_job_status(self, user_id, job_id):
        """Get job status from storage"""
        return get_job_from_firestore(user_id, job_id)
