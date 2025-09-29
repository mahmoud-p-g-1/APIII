import re
from urllib.parse import urlparse
from config import Config

# Dangerous patterns for security
DANGEROUS_PATTERNS = [
    r'javascript:', r'data:', r'vbscript:', r'file:',
    r'<script', r'</script>', r'eval\(', r'document\.cookie',
    r'\.\./', r'%2e%2e%2f', r'%252e%252e%252f',
    r'\x00', r'\r', r'\n', r'%00', r'%0d', r'%0a',
    r'cmd=', r'exec=', r'system\(', r'passthru\(',
    r'shell_exec\(', r'phpinfo\(', r'base64_decode\(',
    r'python -c', r'perl -e', r'ruby -e', r'bash -c'
]

ALLOWED_DOMAINS = [
    'amazon.com', 'www.amazon.com',
    'alibaba.com', 'www.alibaba.com',
    'aliexpress.com', 'www.aliexpress.com', 'www.aliexpress.us',
    'ebay.com', 'www.ebay.com',
    'hm.com', 'www.hm.com', 'www2.hm.com'
]

def validate_url_security(url):
    """Comprehensive URL security validation"""
    
    # Check URL length
    if len(url) > Config.MAX_URL_LENGTH:
        return False, "URL exceeds maximum length"
    
    # Check for dangerous patterns
    url_lower = url.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, url_lower):
            return False, "URL from Dangerous Site"
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"
    
    # Check scheme
    if parsed.scheme not in ['http', 'https']:
        return False, "Unsupported URL Format"
    
    # Check domain
    domain = parsed.netloc.lower()
    domain_allowed = False
    
    for allowed_domain in ALLOWED_DOMAINS:
        if domain == allowed_domain or domain.endswith('.' + allowed_domain):
            domain_allowed = True
            break
    
    if not domain_allowed:
        return False, "Unsupported URL Format"
    
    return True, "URL is valid"

def detect_platform(url):
    """Detect which platform the URL belongs to"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if 'amazon' in domain:
        return 'amazon'
    elif 'alibaba' in domain and 'aliexpress' not in domain:
        return 'alibaba'
    elif 'aliexpress' in domain:
        return 'aliexpress'
    elif 'ebay' in domain:
        return 'ebay'
    elif 'hm.com' in domain:
        return 'hm'
    else:
        return None
