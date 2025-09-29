# api/validators.py
import re
from urllib.parse import urlparse

def validate_url_format(url):
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def validate_platform_url(url, platform):
    """Validate URL belongs to specific platform"""
    domain_mapping = {
        'amazon': ['amazon.com', 'amazon.co.uk', 'amazon.de'],
        'alibaba': ['alibaba.com'],
        'aliexpress': ['aliexpress.com', 'aliexpress.us'],
        'ebay': ['ebay.com', 'ebay.co.uk'],
        'hm': ['hm.com', 'www2.hm.com']
    }
    
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if platform not in domain_mapping:
        return False
    
    for allowed_domain in domain_mapping[platform]:
        if allowed_domain in domain:
            return True
    
    return False

def sanitize_url(url):
    """Sanitize URL to prevent injection attacks"""
    # Remove any control characters
    url = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', url)
    
    # Limit URL length
    if len(url) > 2048:
        return None
    
    return url.strip()
