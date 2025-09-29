from functools import wraps
from flask import request, jsonify
from firebase_config import verify_token

def require_auth(f):
    """Decorator to require Firebase authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'No authentication token provided'}), 401
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Invalid authentication token'}), 401
        
        request.user = user
        return f(*args, **kwargs)
    
    return decorated_function
