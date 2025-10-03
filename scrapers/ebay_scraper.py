from base_scraper import BaseScraper
from urllib.parse import urlparse
import hashlib
from datetime import datetime
import re

class EbayScraper(BaseScraper):
    """eBay-specific scraper class"""
    
    def __init__(self):
        super().__init__()
        self.platform = 'ebay'
        self.allowed_domains = [
            'ebay.com', 'www.ebay.com', 'ebay.co.uk', 'www.ebay.co.uk',
            'ebay.de', 'www.ebay.de', 'ebay.fr', 'www.ebay.fr',
            'ebay.it', 'www.ebay.it', 'ebay.es', 'www.ebay.es',
            'ebay.ca', 'www.ebay.ca', 'ebay.com.au', 'www.ebay.com.au'
        ]
        
        # Add forbidden underwear keywords
        self.forbidden_keywords = [
            'underwear', 'bra', 'panties', 'boxers', 'briefs', 'lingerie',
            'thong', 'g-string', 'corset', 'bustier', 'negligee', 'chemise',
            'teddy', 'bodysuit', 'shapewear', 'pantyhose', 'stockings',
            'garter', 'intimate', 'undergarment', 'brassiere', 'camisole',
            'slip', 'girdle', 'foundation garment'
        ]
    
    def validate_url(self, url):
        """Security: eBay URL validation"""
        try:
            parsed = urlparse(url)
            
            domain_valid = False
            for allowed_domain in self.allowed_domains:
                if parsed.netloc.lower() == allowed_domain:
                    domain_valid = True
                    break
            
            if not domain_valid:
                self.logger.error(f"Invalid domain: {parsed.netloc}")
                return False, "Only eBay domains are allowed"
            
            if parsed.scheme.lower() not in ['http', 'https']:
                self.logger.error(f"Invalid URL scheme: {parsed.scheme}")
                return False, "Only HTTP/HTTPS protocols are allowed"
            
            suspicious_patterns = [
                'javascript:', 'data:', 'file:', 'ftp:',
                '<script', '</script>', 'eval(', 'document.cookie'
            ]
            
            url_lower = url.lower()
            for pattern in suspicious_patterns:
                if pattern in url_lower:
                    self.logger.error(f"Suspicious pattern detected: {pattern}")
                    return False, f"Suspicious pattern detected in URL: {pattern}"
            
            if len(url) > 2048:
                self.logger.error("URL too long")
                return False, "URL exceeds maximum length"
            
            # Check for eBay item URL patterns
            if not any(pattern in url for pattern in ['/itm/', '/i/', 'item=']):
                self.logger.error("Invalid eBay item URL format")
                return False, "Invalid eBay item URL format"
            
            return True, "URL is valid"
            
        except Exception as e:
            self.logger.error(f"URL validation error: {str(e)}")
            return False, f"URL validation failed: {str(e)}"
    
    def is_clothing_product(self, soup, url):
        """Validate if the eBay product is clothing-related (excluding underwear)"""
        try:
            self.logger.info(f"Validating clothing product on eBay...")
            
            url_lower = url.lower()
            
            # Check for FORBIDDEN underwear keywords in URL
            for keyword in self.forbidden_keywords:
                if keyword in url_lower:
                    self.logger.warning(f"Found FORBIDDEN underwear keyword '{keyword}' in URL - REJECTING")
                    return False
            
            # Check for NON-CLOTHING indicators in URL
            non_clothing_url_indicators = [
                'iphone', 'phone', 'mobile', 'smartphone', 'electronics', 'tools',
                'hardware', 'computer', 'laptop', 'tablet', 'camera', 'headphone',
                'speaker', 'charger', 'cable', 'battery', 'automotive', 'car',
                'home-garden', 'kitchen', 'furniture', 'sports-entertainment',
                'collectibles', 'coins', 'stamps', 'antiques', 'books', 'dvd',
                'video-games', 'console', 'toys', 'hobbies'
            ]
            
            for indicator in non_clothing_url_indicators:
                if indicator in url_lower:
                    self.logger.warning(f"Found NON-CLOTHING indicator '{indicator}' in URL - REJECTING")
                    return False
            
            # Check title - eBay uses various selectors
            title_selectors = [
                'h1.x-item-title__mainTitle',
                '.x-item-title__mainTitle',
                'h1[itemprop="name"]',
                '.it-ttl',
                '#itemTitle',
                'h1'
            ]
            
            title = ""
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    title = self.sanitize_input(title_element.get_text().lower().strip())
                    if title:
                        break
            
            if title:
                self.logger.info(f"Found title: {title[:100]}...")
                
                # Check for FORBIDDEN underwear keywords in title
                for keyword in self.forbidden_keywords:
                    if keyword in title:
                        self.logger.warning(f"Found FORBIDDEN underwear keyword '{keyword}' in title - REJECTING")
                        return False
                
                # Check for NON-CLOTHING keywords
                non_clothing_title_keywords = [
                    'iphone', 'phone', 'smartphone', 'mobile', 'android', 'samsung',
                    'computer', 'laptop', 'tablet', 'ipad', 'macbook', 'pc',
                    'headphone', 'earphone', 'speaker', 'bluetooth', 'wireless',
                    'charger', 'cable', 'adapter', 'battery', 'power bank',
                    'camera', 'lens', 'tripod', 'flash', 'memory card',
                    'tool', 'hammer', 'screwdriver', 'drill', 'saw',
                    'kitchen', 'cookware', 'utensil', 'appliance',
                    'furniture', 'chair', 'table', 'desk', 'bed',
                    'car', 'automotive', 'vehicle', 'motorcycle',
                    'game', 'gaming', 'console', 'controller',
                    'book', 'dvd', 'blu-ray', 'cd', 'vinyl',
                    'coin', 'stamp', 'collectible', 'antique'
                ]
                
                for keyword in non_clothing_title_keywords:
                    if keyword in title:
                        self.logger.warning(f"Found NON-CLOTHING keyword '{keyword}' in title - REJECTING")
                        return False
                
                # Check for ALLOWED clothing keywords (excluding underwear)
                allowed_clothing_keywords = [
                    'shirt', 'blouse', 't-shirt', 'tee', 'tank', 'top', 'sweater',
                    'hoodie', 'cardigan', 'jacket', 'blazer', 'coat', 'pants',
                    'jeans', 'trousers', 'shorts', 'skirt', 'leggings', 'dress',
                    'gown', 'suit', 'vest', 'outerwear', 'clothing', 'apparel',
                    'fashion', 'wear'
                ]
                
                for keyword in allowed_clothing_keywords:
                    if keyword in title:
                        self.logger.info(f"Found allowed clothing keyword '{keyword}' in title")
                        return True
            
            # Check breadcrumbs
            breadcrumb_selectors = [
                '.vi-VR-breadCrumbs a',
                '.breadcrumb a',
                'nav[aria-label="Breadcrumb"] a',
                '.b-breadcrumb a'
            ]
            
            breadcrumbs = []
            for selector in breadcrumb_selectors:
                breadcrumbs = soup.select(selector)
                if breadcrumbs:
                    break
            
            for breadcrumb in breadcrumbs:
                breadcrumb_text = self.sanitize_input(breadcrumb.get_text().lower().strip())
                
                # Check for FORBIDDEN underwear categories
                for keyword in self.forbidden_keywords:
                    if keyword in breadcrumb_text:
                        self.logger.warning(f"Found FORBIDDEN underwear category in breadcrumbs - REJECTING")
                        return False
                
                # Check for allowed clothing categories
                clothing_breadcrumb_indicators = [
                    'clothing', 'fashion', 'apparel', 'dress', 'shirt',
                    'pants', 'women', 'men', 'shoes', 'accessories'
                ]
                
                for indicator in clothing_breadcrumb_indicators:
                    if indicator in breadcrumb_text:
                        # Double-check it's not underwear
                        if not any(forbidden in breadcrumb_text for forbidden in self.forbidden_keywords):
                            self.logger.info(f"Found CLOTHING category in breadcrumbs")
                            return True
            
            # Check category section
            category_selectors = [
                '.u-flL.iti-act',
                '.vi-VR-breadCrumbs',
                '.categoryText'
            ]
            
            for selector in category_selectors:
                category_element = soup.select_one(selector)
                if category_element:
                    category_text = self.sanitize_input(category_element.get_text().lower())
                    
                    # Check for clothing indicators
                    if any(cat in category_text for cat in ['clothing', 'fashion', 'apparel']):
                        # Make sure it's not underwear
                        if not any(forbidden in category_text for forbidden in self.forbidden_keywords):
                            self.logger.info("Found clothing category")
                            return True
            
            self.logger.warning("Product does not appear to be allowed clothing")
            return False
            
        except Exception as e:
            self.logger.error(f"Clothing validation error: {str(e)}")
            return False
    
    def extract_product_name(self, soup):
        """Extract product name from eBay"""
        selectors = [
            'h1.x-item-title__mainTitle',
            '.x-item-title__mainTitle',
            'h1[itemprop="name"]',
            '.it-ttl',
            '#itemTitle',
            'h1.it-ttl'
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    # Remove "Details about" prefix if present
                    name = self.sanitize_input(element.get_text().strip())
                    name = re.sub(r'^Details about\s+', '', name, flags=re.IGNORECASE)
                    if name:
                        return name
            except Exception:
                continue
        
        return "Product name not found"
    
    def transform_ebay_image_url(self, url):
        """Transform eBay image URL to high resolution"""
        if not url:
            return url
        
        # eBay image URL patterns:
        # From: https://i.ebayimg.com/images/g/KtYAAeSwDSpowgai/s-l140.webp
        # To: https://i.ebayimg.com/images/g/KtYAAeSwDSpowgai/s-l1600.jpg
        
        # Remove size suffixes and get high resolution
        patterns = [
            (r's-l\d+\.(jpg|webp|png)', 's-l1600.jpg'),
            (r's-l\d+\.', 's-l1600.'),
            (r'_\d+\.(jpg|webp|png)', '_57.jpg'),  # For thumbnails
            (r'\$_\d+\.(JPG|jpg|webp|png)', 's-l1600.jpg')
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, url):
                url = re.sub(pattern, replacement, url)
                break
        
        return url
    
    def extract_images(self, soup):
        """Extract at least 5 product images from eBay"""
        images = []
        seen_urls = set()
        
        try:
            # Method 1: Extract from image carousel/gallery
            image_selectors = [
                '.ux-image-carousel-item img',
                '.ux-image-grid-item img',
                '.filmstrip img',
                '.pic img',
                '#icImg',
                '.img-transition-medium img'
            ]
            
            for selector in image_selectors:
                img_elements = soup.select(selector)
                for img in img_elements:
                    if len(images) >= 10:  # Get more to ensure 5 good ones
                        break
                    
                    # Try different attributes
                    img_url = (img.get('src') or 
                              img.get('data-src') or 
                              img.get('data-zoom-src') or
                              img.get('data-srcset', '').split()[0])
                    
                    if img_url:
                        # Transform to high resolution
                        img_url = self.transform_ebay_image_url(img_url)
                        if self.is_valid_image_url(img_url) and img_url not in seen_urls:
                            images.append(img_url)
                            seen_urls.add(img_url)
            
            # Method 2: Extract from JavaScript data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'enlargeImage' in script.string:
                    # Look for image URLs in JavaScript
                    urls = re.findall(r'https://i\.ebayimg\.com/images/[^"\']+', script.string)
                    for url in urls:
                        if len(images) >= 10:
                            break
                        url = self.transform_ebay_image_url(url)
                        if self.is_valid_image_url(url) and url not in seen_urls:
                            images.append(url)
                            seen_urls.add(url)
            
            # Method 3: Look for meta property images
            meta_images = soup.find_all('meta', {'property': 'og:image'})
            for meta in meta_images:
                if len(images) >= 10:
                    break
                img_url = meta.get('content', '')
                if img_url:
                    img_url = self.transform_ebay_image_url(img_url)
                    if self.is_valid_image_url(img_url) and img_url not in seen_urls:
                        images.append(img_url)
                        seen_urls.add(img_url)
            
            self.logger.info(f"Extracted {len(images)} eBay images")
            return images[:5]  # Return exactly 5 images
            
        except Exception as e:
            self.logger.error(f"eBay image extraction error: {str(e)}")
            return []
    
    def is_valid_image_url(self, url):
        """Validate eBay image URLs"""
        try:
            if not url or not isinstance(url, str):
                return False
            
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # eBay image domains
            ebay_image_domains = [
                'i.ebayimg.com', 'thumbs.ebaystatic.com', 
                'ir.ebaystatic.com', 'p.ebaystatic.com'
            ]
            
            if not any(domain in parsed.netloc for domain in ebay_image_domains):
                return False
            
            # Exclude GIF files
            if url.lower().endswith('.gif'):
                return False
            
            # Exclude placeholder images
            excluded_patterns = ['spacer', 'pixel', 'blank', 'loading']
            url_lower = url.lower()
            for pattern in excluded_patterns:
                if pattern in url_lower:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def scrape(self, url):
        """Main method to scrape eBay product - only platform, name, and images"""
        try:
            is_valid, message = self.validate_url(url)
            if not is_valid:
                self.logger.error(f"URL validation failed: {message}")
                print(f"Security Error: {message}")
                return None
            
            response = self.make_secure_request(url)
            soup = self.secure_parse_html(response.content)
            
            if not self.is_clothing_product(soup, url):
                print("\n" + "="*60)
                print("ERROR: This is not an allowed clothing product!")
                print("Underwear and intimate apparel are not permitted.")
                print("="*60)
                return None
            
            print(f"Clothing product validated on eBay! Proceeding with scraping...")
            
            product_data = {
                'platform': self.platform,
                'name': self.extract_product_name(soup),
                'images': self.extract_images(soup),
                'scraped_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Product data extracted successfully from eBay")
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error in eBay scraping: {str(e)}")
            print(f"Error: {str(e)}")
            return None
