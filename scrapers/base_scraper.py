import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse

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
        
        # Security: Setup logging
        self.setup_logging()
        
        # Security: Session configuration
        self.configure_session()
        
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
        """Security: Make a secure HTTP request with error handling"""
        for attempt in range(self.max_retries):
            try:
                self.session.headers.update(self.get_random_headers())
                
                self.logger.info(f"Making request to: {url[:50]}... (Attempt {attempt + 1})")
                
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
                
                self.logger.info("Request successful")
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
