from datetime import datetime
from firebase_config import db, firebase_initialized
import uuid

class ScrapingJob:
    """Model for scraping jobs"""
    
    def __init__(self, user_id, url, platform):
        self.job_id = str(uuid.uuid4())
        self.user_id = user_id
        self.url = url
        self.platform = platform
        self.status = 'queued'
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.result = None
        self.error = None
    
    def to_dict(self):
        """Convert to dictionary for Firestore"""
        return {
            'job_id': self.job_id,
            'user_id': self.user_id,
            'url': self.url,
            'platform': self.platform,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'result': self.result,
            'error': self.error
        }
    
    def save(self):
        """Save to Firestore"""
        try:
            if not firebase_initialized:
                return False
            doc_ref = db.collection('users').document(self.user_id).collection('scraping_jobs').document(self.job_id)
            doc_ref.set(self.to_dict())
            return True
        except Exception as e:
            print(f"Error saving job: {e}")
            return False
    
    def update_status(self, status, result=None, error=None):
        """Update job status"""
        self.status = status
        self.updated_at = datetime.now().isoformat()
        if result:
            self.result = result
        if error:
            self.error = error
        return self.save()
    
    @classmethod
    def get_by_id(cls, user_id, job_id):
        """Get job by ID"""
        try:
            if not firebase_initialized:
                return None
            doc = db.collection('users').document(user_id).collection('scraping_jobs').document(job_id).get()
            if doc.exists:
                data = doc.to_dict()
                job = cls(data['user_id'], data['url'], data['platform'])
                job.job_id = data['job_id']
                job.status = data['status']
                job.created_at = data['created_at']
                job.updated_at = data['updated_at']
                job.result = data.get('result')
                job.error = data.get('error')
                return job
        except Exception as e:
# models/job.py (continued from line 43)
            print(f"Error getting job: {e}")
        return None
    
    @classmethod
    def get_user_jobs(cls, user_id, limit=10):
        """Get all jobs for a user"""
        try:
            if not firebase_initialized:
                return []
            
            jobs = []
            docs = db.collection('users').document(user_id).collection('scraping_jobs').limit(limit).get()
            
            for doc in docs:
                if doc.exists:
                    data = doc.to_dict()
                    job = cls(data['user_id'], data['url'], data['platform'])
                    job.job_id = data['job_id']
                    job.status = data['status']
                    job.created_at = data['created_at']
                    job.updated_at = data['updated_at']
                    job.result = data.get('result')
                    job.error = data.get('error')
                    jobs.append(job)
            
            return jobs
        except Exception as e:
            print(f"Error getting user jobs: {e}")
        return []
    
    @classmethod
    def delete_old_jobs(cls, days_old=7):
        """Delete jobs older than specified days"""
        try:
            if not firebase_initialized:
                return 0
            
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_str = cutoff_date.isoformat()
            
            # This would need to be implemented with Firestore batch operations
            # For now, return 0
            return 0
        except Exception as e:
            print(f"Error deleting old jobs: {e}")
        return 0
