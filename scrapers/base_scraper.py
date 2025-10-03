import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import os
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse, urlencode

# Add ScrapingBee import
from scrapingbee import ScrapingBeeClient

class BaseScraper:
    """Base scraper class with common functionality for all platforms"""
    
    def __init__(self):
        self.session = requests.Session()
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        
        # Security: Set secure headers
        self.base_headers = {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Security: Rate limiting
        self.request_times = []
        self.max_requests_per_minute = 10
        self.min_delay_between_requests = 2
        self.max_delay_between_requests = 5
        
        # Security: Request timeout
        self.timeout = 30
        
        # Security: Maximum retries
        self.max_retries = 3
        
        # ScrapingBee configuration
        self.scrapingbee_api_key = os.getenv('SCRAPINGBEE_API_KEY')
        self.use_scrapingbee = bool(self.scrapingbee_api_key)
        
        # Initialize ScrapingBee client
        if self.use_scrapingbee:
            self.scrapingbee_client = ScrapingBeeClient(api_key=self.scrapingbee_api_key)
        else:
            self.scrapingbee_client = None
        
        # ScrapingBee settings for different platforms
        self.scrapingbee_settings = {
            'aliexpress': {
                'render_js': True,
                'premium_proxy': True,
                'wait': 3000,
                'country_code': 'us',
                'block_ads': True,
                'block_resources': False
            },
            'amazon': {
                'render_js': True,
                'premium_proxy': True,
                'wait': 2000,
                'country_code': 'us',
                'block_ads': True,
                'block_resources': False
            },
            'hm': {
                'render_js': True,
                'premium_proxy': True,
                'wait': 3000,
                'country_code': 'us',
                'block_ads': True,
                'block_resources': False
            },
            'ebay': {
                'render_js': False,
                'premium_proxy': True,
                'wait': 1000,
                'country_code': 'us',
                'block_ads': True,
                'block_resources': True
            },
            'alibaba': {
                'render_js': True,
                'premium_proxy': True,
                'wait': 2500,
                'country_code': 'us',
                'block_ads': True,
                'block_resources': False
            }
        }
        
        # Security: Setup logging
        self.setup_logging()
        
        # Security: Session configuration
        self.configure_session()
        
        if self.use_scrapingbee:
            self.logger.info("ScrapingBee integration enabled")
        else:
            self.logger.warning("ScrapingBee API key not found, using direct requests")
        
        # Clothing validation data
        self.clothing_keywords = {
            'tops': ['shirt', 'blouse', 't-shirt', 'tee', 'tank', 'top', 'sweater', 'hoodie', 'cardigan', 'jacket', 'blazer', 'coat'],
            'bottoms': ['pants', 'jeans', 'trousers', 'shorts', 'skirt', 'leggings', 'joggers', 'sweatpants'],
            'dresses': ['dress', 'gown', 'frock', 'sundress', 'maxi dress', 'mini dress'],
            'underwear': ['underwear', 'bra', 'panties', 'boxers', 'briefs', 'lingerie'],
            'activewear': ['activewear', 'sportswear', 'athletic', 'workout', 'gym', 'yoga pants', 'sports bra'],
            'outerwear': ['outerwear', 'winter coat', 'parka', 'windbreaker', 'vest'],
            'sleepwear': ['pajamas', 'nightgown', 'sleepwear', 'robe'],
            'accessories': ['scarf', 'hat', 'gloves', 'belt', 'tie', 'bow tie'],
            'footwear': ['shoes', 'boots', 'sneakers', 'sandals', 'heels', 'flats', 'loafers']
        }
        
        self.clothing_departments = [
            'clothing', 'fashion', 'apparel', 'mens-clothing', 'womens-clothing', 
            'boys-clothing', 'girls-clothing', 'baby-clothing', 'shoes', 'handbags',
            'accessories', 'dresses', 'casual-dresses', 'womens-dresses'
        ]
    
    def setup_logging(self):
        """Security: Setup secure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper_security.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def configure_session(self):
        """Security: Configure session with security settings"""
        self.session.verify = True
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=1,
            pool_maxsize=1,
            max_retries=0
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def should_use_scrapingbee(self, url):
        """Determine if ScrapingBee should be used for this URL"""
        if not self.use_scrapingbee:
            return False
        
        # JavaScript-heavy sites that benefit from ScrapingBee
        js_heavy_domains = [
            'aliexpress.com', 'alibaba.com', 'hm.com'
        ]
        
        # High-blocking sites that need premium proxies
        high_blocking_domains = [
            'amazon.com', 'aliexpress.com', 'alibaba.com'
        ]
        
        url_lower = url.lower()
        
        # Use ScrapingBee for JS-heavy or high-blocking sites
        return any(domain in url_lower for domain in js_heavy_domains + high_blocking_domains)
    
    def get_scrapingbee_settings(self, url):
        """Get ScrapingBee settings based on platform"""
        url_lower = url.lower()
        
        # Determine platform from URL
        if 'aliexpress.com' in url_lower:
            return self.scrapingbee_settings.get('aliexpress', {})
        elif 'amazon.com' in url_lower:
            return self.scrapingbee_settings.get('amazon', {})
        elif 'hm.com' in url_lower:
            return self.scrapingbee_settings.get('hm', {})
        elif 'ebay.com' in url_lower:
            return self.scrapingbee_settings.get('ebay', {})
        elif 'alibaba.com' in url_lower:
            return self.scrapingbee_settings.get('alibaba', {})
        else:
            # Default settings
            return {
                'render_js': True,
                'premium_proxy': True,
                'wait': 2000,
                'country_code': 'us',
                'block_ads': True,
                'block_resources': False
            }
    
    def make_scrapingbee_request(self, url, **kwargs):
        """Make request through ScrapingBee API using official client"""
        if not self.scrapingbee_client:
            raise ValueError("ScrapingBee client not configured")
        
        # Get platform-specific settings
        platform_settings = self.get_scrapingbee_settings(url)
        
        # Merge with any provided kwargs
        settings = {**platform_settings, **kwargs}
        
        try:
            self.logger.info(f"Making ScrapingBee request to: {url[:50]}...")
            self.logger.info(f"Settings: JS={settings.get('render_js')}, Premium={settings.get('premium_proxy')}, Wait={settings.get('wait')}ms")
            
            # Use the official ScrapingBee client
            response = self.scrapingbee_client.get(
                url,
                params=settings,
                retries=2  # Built-in retry mechanism
            )
            
            # Log ScrapingBee metrics (available in response headers)
            if hasattr(response, 'headers'):
                if 'Spb-Cost' in response.headers:
                    cost = response.headers['Spb-Cost']
                    self.logger.info(f"ScrapingBee request cost: {cost} credits")
                
                if 'Spb-Response-Code' in response.headers:
                    original_status = response.headers['Spb-Response-Code']
                    self.logger.info(f"Original response status: {original_status}")
                
                if 'Spb-Proxy-Country' in response.headers:
                    proxy_country = response.headers['Spb-Proxy-Country']
                    self.logger.info(f"Proxy country: {proxy_country}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"ScrapingBee request failed: {str(e)}")
            raise

    def rate_limit_decorator(func):
        """Security: Rate limiting decorator"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            current_time = datetime.now()
            
            self.request_times = [
                req_time for req_time in self.request_times 
                if current_time - req_time < timedelta(minutes=1)
            ]
            
            if len(self.request_times) >= self.max_requests_per_minute:
                wait_time = 60 - (current_time - self.request_times[0]).seconds
                self.logger.warning(f"Rate limit reached. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                self.request_times = []
            
            self.request_times.append(current_time)
            
            # Reduce delay when using ScrapingBee (they handle rate limiting)
            if hasattr(self, '_using_scrapingbee') and self._using_scrapingbee:
                delay = random.uniform(0.5, 1.5)
            else:
                delay = random.uniform(self.min_delay_between_requests, self.max_delay_between_requests)
            
            time.sleep(delay)
            
            return func(self, *args, **kwargs)
        return wrapper
    
    def sanitize_input(self, text):
        """Security: Sanitize text input to prevent XSS and injection attacks"""
        if not isinstance(text, str):
            return str(text)
        
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        text = text[:1000]
        text = ' '.join(text.split())
        
        return text.strip()
    
    def get_random_headers(self):
        """Security: Generate random headers for each request"""
        headers = self.base_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        
        if random.random() < 0.3:
            headers['DNT'] = '1'
        if random.random() < 0.2:
            headers['Sec-GPC'] = '1'
        
        return headers
    
    @rate_limit_decorator
    def make_secure_request(self, url):
        """Security: Make a secure HTTP request with ScrapingBee fallback"""
        
        # Check if we should use ScrapingBee for this URL
        should_use_sb = self.should_use_scrapingbee(url)
        
        if should_use_sb:
            try:
                self._using_scrapingbee = True
                response = self.make_scrapingbee_request(url)
                self.logger.info("ScrapingBee request successful")
                return response
            except Exception as e:
                self.logger.warning(f"ScrapingBee failed, falling back to direct request: {str(e)}")
                self._using_scrapingbee = False
        
        # Fallback to ScrapingBee without JS rendering if available
        if self.use_scrapingbee and not should_use_sb:
            try:
                self._using_scrapingbee = True
                response = self.make_scrapingbee_request(
                    url,
                    render_js=False,
                    premium_proxy=True,
                    wait=1000
                )
                self.logger.info("ScrapingBee fallback request successful")
                return response
            except Exception as e:
                self.logger.warning(f"ScrapingBee fallback failed: {str(e)}")
                self._using_scrapingbee = False
        
        # Direct request as final fallback
        self._using_scrapingbee = False
        for attempt in range(self.max_retries):
            try:
                self.session.headers.update(self.get_random_headers())
                
                self.logger.info(f"Making direct request to: {url[:50]}... (Attempt {attempt + 1})")
                
                response = self.session.get(
                    url, 
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=False
                )
                
                response.raise_for_status()
                
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    raise ValueError(f"Unexpected content type: {content_type}")
                
                if len(response.content) > 10 * 1024 * 1024:
                    raise ValueError("Response too large")
                
                self.logger.info("Direct request successful")
                return response
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
                
            except Exception as e:
                self.logger.error(f"Unexpected error (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        
        raise Exception("All retry attempts failed")
    
    def secure_parse_html(self, html_content):
        """Security: Safely parse HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup
        except Exception as e:
            self.logger.error(f"HTML parsing error: {str(e)}")
            raise ValueError(f"Failed to parse HTML: {str(e)}")
    
    def get_scrapingbee_usage_stats(self):
        """Get ScrapingBee usage statistics (if available)"""
        if not self.scrapingbee_client:
            return None
        
        try:
            # The official client doesn't have a direct usage method,
            # but we can make a simple request to check
            response = self.scrapingbee_client.get(
                'https://httpbin.org/status/200',
                params={'render_js': False}
            )
            
            if hasattr(response, 'headers') and 'Spb-Cost' in response.headers:
                return {
                    'status': 'active',
                    'last_request_cost': response.headers.get('Spb-Cost', 'unknown')
                }
            
            return {'status': 'active'}
                
        except Exception as e:
            self.logger.warning(f"Error checking ScrapingBee status: {str(e)}")
            return None
