from .base_scraper import BaseScraper
from urllib.parse import urlparse
import hashlib
from datetime import datetime
import re

class AlibabaScraper(BaseScraper):
    """Alibaba-specific scraper class"""
    
    def __init__(self):
        super().__init__()
        self.platform = 'alibaba'
        self.allowed_domains = ['alibaba.com', 'www.alibaba.com']
        
        # Add forbidden underwear keywords
        self.forbidden_keywords = [
            'underwear', 'bra', 'panties', 'boxers', 'briefs', 'lingerie',
            'thong', 'g-string', 'corset', 'bustier', 'negligee', 'chemise',
            'teddy', 'bodysuit', 'shapewear', 'pantyhose', 'stockings',
            'garter', 'intimate', 'undergarment'
        ]
    
    def validate_url(self, url):
        """Security: Alibaba URL validation"""
        try:
            parsed = urlparse(url)
            
            if parsed.netloc.lower() not in self.allowed_domains:
                self.logger.error(f"Invalid domain: {parsed.netloc}")
                return False, "Only Alibaba domains are allowed"
            
            if parsed.scheme.lower() not in ['http', 'https']:
                self.logger.error(f"Invalid URL scheme: {parsed.scheme}")
                return False, "Only HTTP/HTTPS protocols are allowed"
            
            if len(url) > 2048:
                self.logger.error("URL too long")
                return False, "URL exceeds maximum length"
            
            if '/product-detail/' not in url:
                self.logger.error("Invalid Alibaba product URL format")
                return False, "Invalid Alibaba product URL format"
            
            return True, "URL is valid"
            
        except Exception as e:
            self.logger.error(f"URL validation error: {str(e)}")
            return False, f"URL validation failed: {str(e)}"
    
    def is_clothing_product(self, soup, url):
        """Validate if the Alibaba product is clothing-related (excluding underwear)"""
        try:
            self.logger.info(f"Validating clothing product on Alibaba...")
            
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
                'home-garden', 'kitchen', 'furniture', 'sports-entertainment'
            ]
            
            for indicator in non_clothing_url_indicators:
                if indicator in url_lower:
                    self.logger.warning(f"Found NON-CLOTHING indicator '{indicator}' in URL - REJECTING")
                    return False
            
            # Check title
            title_selectors = [
                'h1[title]',
                '.product-title-container h1',
                '.product-title', 
                'h1.product-name'
            ]
            
            title_element = None
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    break
            
            if title_element:
                title = title_element.get('title', '') or title_element.get_text()
                title = self.sanitize_input(title.lower().strip())
                self.logger.info(f"Found title: {title[:100]}...")
                
                # Check for FORBIDDEN underwear keywords in title
                for keyword in self.forbidden_keywords:
                    if keyword in title:
                        self.logger.warning(f"Found FORBIDDEN underwear keyword '{keyword}' in title - REJECTING")
                        return False
                
                # Check for NON-CLOTHING keywords
                non_clothing_title_keywords = [
                    'iphone', 'phone', 'smartphone', 'mobile', 'android',
                    'computer', 'laptop', 'tablet', 'headphone', 'speaker',
                    'charger', 'cable', 'battery', 'camera', 'tool',
                    'kitchen', 'furniture', 'car', 'automotive', 'game'
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
                    'gown', 'suit', 'vest', 'outerwear'
                ]
                
                for keyword in allowed_clothing_keywords:
                    if keyword in title:
                        self.logger.info(f"Found allowed clothing keyword '{keyword}' in title")
                        return True
            
            # Check breadcrumbs
            breadcrumb_selectors = [
                '.detail-breadcrumb-layout nav ol li a',
                '.module_breadcrumbNew nav ol li a',
                'nav[aria-label="breadcrumb"] ol li a'
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
                    'apparel', 'clothing', 'fashion', 'dress', 'shirt',
                    'pants', 'women', 'men', 'casual', 'formal'
                ]
                
                for indicator in clothing_breadcrumb_indicators:
                    if indicator in breadcrumb_text:
                        # Double-check it's not underwear
                        if not any(forbidden in breadcrumb_text for forbidden in self.forbidden_keywords):
                            self.logger.info(f"Found CLOTHING category in breadcrumbs")
                            return True
            
            self.logger.warning("Product does not appear to be allowed clothing")
            return False
            
        except Exception as e:
            self.logger.error(f"Clothing validation error: {str(e)}")
            return False
    
    def extract_product_name(self, soup):
        """Extract product name from Alibaba"""
        selectors = [
            'h1[title]',
            '.product-title-container h1',
            '.product-title', 
            'h1.product-name'
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    name = element.get('title', '') or element.get_text()
                    name = self.sanitize_input(name.strip())
                    if name:
                        return name
            except Exception:
                continue
        
        return "Product name not found"
    
    def transform_alibaba_image_url(self, url):
        """Transform Alibaba image URL to high resolution"""
        if not url:
            return url
            
        # Ensure URL has protocol
        if url.startswith('//'):
            url = 'https:' + url
            
        # Transform thumbnail to high resolution
        # From: https://s.alicdn.com/@sc04/kf/Hfb0a02d0ec7a440d9fc2b90b4d6ea7bdt.jpg_80x80.jpg
        # To: https://s.alicdn.com/@sc04/kf/Hfb0a02d0ec7a440d9fc2b90b4d6ea7bdt.jpg_1000x1000.jpg
        
        # Remove existing size suffixes and add high resolution
        patterns = [
            (r'_\d+x\d+\.jpg', '_1000x1000.jpg'),
            (r'_\d+x\d+\.png', '_1000x1000.png'),
            (r'\.jpg_\d+x\d+\.jpg', '.jpg_1000x1000.jpg'),
            (r'\.png_\d+x\d+\.png', '.png_1000x1000.png')
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, url):
                url = re.sub(pattern, replacement, url)
                return url
        
        # If no pattern matched, append size suffix
        if url.endswith('.jpg'):
            url = url.replace('.jpg', '_1000x1000.jpg')
        elif url.endswith('.png'):
            url = url.replace('.png', '_1000x1000.png')
        else:
            url += '_1000x1000.jpg'
        
        return url
    
    def extract_images(self, soup):
        """Extract at least 5 product images from Alibaba"""
        images = []
        seen_urls = set()
        
        try:
            # Method 1: Extract from background-image style attributes
            image_elements = soup.select('[style*="background-image"]')
            for element in image_elements:
                if len(images) >= 10:
                    break
                style = element.get('style', '')
                if 'background-image' in style:
                    url_match = re.search(r'background-image:\s*url\(["\']?(//[^"\']+)["\']?\)', style)
                    if url_match:
                        img_url = url_match.group(1)
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        
                        # Transform to high resolution
                        img_url = self.transform_alibaba_image_url(img_url)
                        
                        if img_url not in seen_urls and self.is_valid_image_url(img_url):
                            images.append(img_url)
                            seen_urls.add(img_url)
            
            # Method 2: Regular img tags
            img_tags = soup.select('img[src*="alicdn.com"]')
            for img in img_tags:
                if len(images) >= 10:
                    break
                img_url = img.get('src')
                if img_url:
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    
                    # Transform to high resolution
                    img_url = self.transform_alibaba_image_url(img_url)
                    
                    if img_url not in seen_urls and self.is_valid_image_url(img_url):
                        images.append(img_url)
                        seen_urls.add(img_url)
            
            self.logger.info(f"Extracted {len(images)} Alibaba images")
            return images[:5]  # Return exactly 5 images
            
        except Exception as e:
            self.logger.error(f"Alibaba image extraction error: {str(e)}")
            return []
    
    def is_valid_image_url(self, url):
        """Validate Alibaba image URLs"""
        try:
            if not url or not isinstance(url, str):
                return False
            
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            alibaba_image_domains = [
                'alicdn.com', 's.alicdn.com', 'sc04.alicdn.com',
                'sc01.alicdn.com', 'sc02.alicdn.com', 'sc03.alicdn.com',
                'cbu01.alicdn.com', 'img.alicdn.com', 'gw.alicdn.com'
            ]
            
            if not any(domain in parsed.netloc for domain in alibaba_image_domains):
                return False
            
            if url.lower().endswith('.gif'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def scrape(self, url):
        """Main method to scrape Alibaba product - only platform, name, and images"""
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
            
            print(f"Clothing product validated on Alibaba! Proceeding with scraping...")
            
            product_data = {
                'platform': self.platform,
                'name': self.extract_product_name(soup),
                'images': self.extract_images(soup),
                'scraped_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Product data extracted successfully from Alibaba")
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error in Alibaba scraping: {str(e)}")
            print(f"Error: {str(e)}")
            return None
