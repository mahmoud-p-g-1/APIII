import queue
import threading
from datetime import datetime, timedelta
from config import Config

class QueueManager:
    """In-memory queue manager to replace Redis"""
    
    def __init__(self):
        self.job_queue = queue.Queue(maxsize=Config.MAX_QUEUE_SIZE)
        self.rate_limit_data = {}
        self.cache_data = {}
        self.lock = threading.Lock()
    
    def add_job(self, job_data):
        """Add job to queue"""
        try:
            self.job_queue.put(job_data, block=False)
            return True
        except queue.Full:
            return False
    
    def get_job(self, timeout=1):
        """Get job from queue"""
        try:
            return self.job_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def check_rate_limit(self, client_id, endpoint, max_requests, window_minutes):
        """Check rate limit for client"""
        with self.lock:
            current_time = datetime.now()
            key = f"{endpoint}:{client_id}"
            
            # Clean old entries
            if key in self.rate_limit_data:
                self.rate_limit_data[key] = [
                    req_time for req_time in self.rate_limit_data[key]
                    if current_time - req_time < timedelta(minutes=window_minutes)
                ]
            else:
                self.rate_limit_data[key] = []
            
            # Check limit
            if len(self.rate_limit_data[key]) >= max_requests:
                return False
            
            # Add current request
            self.rate_limit_data[key].append(current_time)
            return True
    
    def get_cache(self, key):
        """Get cached value"""
        with self.lock:
            if key in self.cache_data:
                data, expiry = self.cache_data[key]
                if datetime.now() < expiry:
                    return data
                else:
                    del self.cache_data[key]
            return None
    
    def set_cache(self, key, value, ttl_seconds=3600):
        """Set cached value with TTL"""
        with self.lock:
            expiry = datetime.now() + timedelta(seconds=ttl_seconds)
            self.cache_data[key] = (value, expiry)
    
    def get_queue_size(self):
        """Get current queue size"""
        return self.job_queue.qsize()

# Global queue manager instance
queue_manager = QueueManager()
