from queue_manager import queue_manager
import hashlib

def get_cache_key(url):
    """Generate cache key from URL"""
    return f"cache:{hashlib.md5(url.encode()).hexdigest()}"

def get_cached_result(url):
    """Get cached scraping result"""
    try:
        key = get_cache_key(url)
        return queue_manager.get_cache(key)
    except Exception as e:
        print(f"Cache retrieval error: {e}")
    return None

def set_cached_result(url, result, ttl=3600):
    """Cache scraping result"""
    try:
        key = get_cache_key(url)
        queue_manager.set_cache(key, result, ttl)
        return True
    except Exception as e:
        print(f"Cache storage error: {e}")
    return False
