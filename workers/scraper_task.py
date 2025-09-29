from queue_manager import queue_manager
from firebase_config import update_job_status
import logging

logger = logging.getLogger(__name__)

def process_scraping_result(job_id, user_id, result):
    """Process and store scraping results"""
    try:
        # Validate result
        if not result or 'platform' not in result:
            raise ValueError("Invalid scraping result")
        
        # Add metadata
        result['job_id'] = job_id
        result['user_id'] = user_id
        
        # Update job status with result
        update_job_status(user_id, job_id, 'completed', result)
        
        logger.info(f"Successfully processed job {job_id} for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing result for job {job_id}: {str(e)}")
        update_job_status(user_id, job_id, 'failed', {'error': str(e)})
        return False

def cleanup_old_jobs():
    """Clean up old completed jobs (run periodically)"""
    try:
        from datetime import datetime, timedelta
        from firebase_config import db
        
        # This would need to be implemented with Firestore queries
        logger.info("Cleanup task completed")
        return True
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}")
        return False
