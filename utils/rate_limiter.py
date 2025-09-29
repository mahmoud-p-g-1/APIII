from functools import wraps
from flask import request, jsonify
from queue_manager import queue_manager
from config import Config

def check_rate_limit(client_id, endpoint, max_requests, window_minutes):
    """Check rate limit for a client"""
    return queue_manager.check_rate_limit(client_id, endpoint, max_requests, window_minutes)

def rate_limit(max_requests=1000, window_minutes=1000):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier
            if hasattr(request, 'user'):
                client_id = request.user['uid']
            else:
                client_id = request.remote_addr
            
            # Check rate limit
            if not check_rate_limit(client_id, f.__name__, max_requests, window_minutes):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'max_requests': max_requests,
                    'window_minutes': window_minutes
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
