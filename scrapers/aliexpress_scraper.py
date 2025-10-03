from base_scraper import BaseScraper
from urllib.parse import urlparse
import hashlib
from datetime import datetime
import re
import json

class AliExpressScraper(BaseScraper):
    """AliExpress-specific scraper class"""
    
    def __init__(self):
        super().__init__()
        self.platform = 'aliexpress'
        self.allowed_domains = [
            'aliexpress.com', 'www.aliexpress.com', 'www.aliexpress.us',
            'm.aliexpress.com', 'es.aliexpress.com', 'pt.aliexpress.com',
            'fr.aliexpress.com', 'de.aliexpress.com', 'it.aliexpress.com',
            'ru.aliexpress.com', 'nl.aliexpress.com', 'pl.aliexpress.com'
        ]
        
        # Add forbidden underwear keywords
        self.forbidden_keywords = [
            'underwear', 'bra', 'panties', 'boxers', 'briefs', 'lingerie',
            'thong', 'g-string', 'corset', 'bustier', 'negligee', 'chemise',
            'teddy', 'bodysuit', 'shapewear', 'pantyhose', 'stockings',
            'garter', 'intimate', 'undergarment', 'brassiere', 'camisole',
            'slip', 'girdle', 'foundation garment'
        ]
    
    def safe_log(self, message):
        """Safely log messages that might contain Unicode characters"""
        try:
            # First try to log normally
            self.logger.info(message)
        except UnicodeEncodeError:
            try:
                # If that fails, encode to ASCII with replacement
                safe_message = message.encode('ascii', 'replace').decode('ascii')
                self.logger.info(safe_message)
            except Exception:
                # Final fallback - just log that we found a title
                self.logger.info("Found product title (contains special characters)")
        except Exception as e:
            # Any other error, log safely
            self.logger.info(f"Logging error occurred: {str(e)}")

    
    def validate_url(self, url):
        """Security: AliExpress URL validation"""
        try:
            parsed = urlparse(url)
            
            domain_valid = False
            for allowed_domain in self.allowed_domains:
                if parsed.netloc.lower() == allowed_domain or parsed.netloc.lower().endswith('.' + allowed_domain):
                    domain_valid = True
                    break
            
            if not domain_valid:
                self.logger.error(f"Invalid domain: {parsed.netloc}")
                return False, "Only AliExpress domains are allowed"
            
            if parsed.scheme.lower() not in ['http', 'https']:
                self.logger.error(f"Invalid URL scheme: {parsed.scheme}")
                return False, "Only HTTP/HTTPS protocols are allowed"
            
            if len(url) > 2048:
                self.logger.error("URL too long")
                return False, "URL exceeds maximum length"
            
            if not any(pattern in url for pattern in ['/item/', '.html', 'productId=']):
                self.logger.error("Invalid AliExpress product URL format")
                return False, "Invalid AliExpress product URL format"
            
            return True, "URL is valid"
            
        except Exception as e:
            self.logger.error(f"URL validation error: {str(e)}")
            return False, f"URL validation failed: {str(e)}"
    
    def extract_json_data(self, soup):
        """Extract JSON data from window._d_c_.DCData"""
        try:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    if 'window._d_c_.DCData' in script.string:
                        match = re.search(r'window\._d_c_\.DCData\s*=\s*({.*?});', script.string, re.DOTALL)
                        if match:
                            try:
                                json_data = json.loads(match.group(1))
                                self.safe_log("Successfully extracted DCData JSON")
                                return json_data
                            except json.JSONDecodeError:
                                continue
                    
                    if 'window.runParams' in script.string:
                        match = re.search(r'window\.runParams\s*=\s*({.*?});', script.string, re.DOTALL)
                        if match:
                            try:
                                json_data = json.loads(match.group(1))
                                self.safe_log("Successfully extracted runParams JSON")
                                return json_data
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            self.logger.warning(f"Error extracting JSON data: {str(e)}")
        return None
    
    def is_clothing_product(self, soup, url):
        """Validate if the AliExpress product is clothing-related (excluding underwear)"""
        try:
            self.safe_log(f"Validating clothing product on AliExpress...")
            
            url_lower = url.lower()
            
            # Check for FORBIDDEN underwear keywords in URL
            for keyword in self.forbidden_keywords:
                if keyword in url_lower:
                    self.logger.warning(f"Found FORBIDDEN underwear keyword '{keyword}' in URL - REJECTING")
                    return False
            
            # Check for NON-CLOTHING indicators in URL
            non_clothing_url_indicators = [
                'phone', 'mobile', 'smartphone', 'electronics', 'tools',
                'hardware', 'computer', 'laptop', 'tablet', 'camera',
                'headphone', 'speaker', 'charger', 'cable', 'battery',
                'automotive', 'car', 'home-garden', 'kitchen', 'furniture'
            ]
            
            for indicator in non_clothing_url_indicators:
                if indicator in url_lower:
                    self.logger.warning(f"Found NON-CLOTHING indicator '{indicator}' in URL - REJECTING")
                    return False
            
            # Extract JSON data for validation
            json_data = self.extract_json_data(soup)
            
            # Check title
            title = ""
            title_meta = soup.find('meta', {'property': 'og:title'})
            if title_meta:
                title = self.sanitize_input(title_meta.get('content', '').lower())
            
            if not title and json_data:
                if 'name' in json_data and json_data['name'] != 'ItemDetailResp':
                    title = self.sanitize_input(json_data['name'].lower())
            
            if title:
                # Safe logging for title that might contain Unicode
                try:
                    self.safe_log(f"Found title: {title[:100]}...")
                except:
                    self.safe_log("Found title (contains special characters)")
                
                # Check for FORBIDDEN underwear keywords in title
                for keyword in self.forbidden_keywords:
                    if keyword in title:
                        self.logger.warning(f"Found FORBIDDEN underwear keyword '{keyword}' in title - REJECTING")
                        return False
                
                # Check for NON-CLOTHING keywords
                non_clothing_keywords = [
                    'iphone', 'phone', 'smartphone', 'computer', 'laptop',
                    'headphone', 'speaker', 'charger', 'cable', 'camera',
                    'tool', 'kitchen', 'furniture', 'car', 'game'
                ]
                
                for keyword in non_clothing_keywords:
                    if keyword in title:
                        self.logger.warning(f"Found NON-CLOTHING keyword '{keyword}' in title - REJECTING")
                        return False
                
                # Check for ALLOWED clothing keywords (excluding underwear)
                allowed_clothing_keywords = [
                    'shirt', 'blouse', 't-shirt', 'tee', 'tank', 'top', 'sweater',
                    'hoodie', 'cardigan', 'jacket', 'blazer', 'coat', 'pants',
                    'jeans', 'trousers', 'shorts', 'skirt', 'leggings', 'dress',
                    'gown', 'suit', 'vest', 'outerwear', 'sequin', 'glitter'
                ]
                
                for keyword in allowed_clothing_keywords:
                    if keyword in title:
                        self.safe_log(f"Found allowed clothing keyword '{keyword}' in title")
                        return True
            
            # If title contains clothing-related words but not underwear, it's valid
            # The product "shirt" should pass validation
            if title and ('shirt' in title or 'top' in title or 'dress' in title or 'pants' in title):
                self.safe_log("Product appears to be allowed clothing")
                return True
            
            # If we can't determine definitively, check if it's NOT underwear
            # and has some clothing indicators
            if title and not any(forbidden in title for forbidden in self.forbidden_keywords):
                self.safe_log("No forbidden keywords found, assuming valid clothing")
                return True
            
            self.logger.warning("Cannot confirm product is allowed clothing")
            return False
            
        except Exception as e:
            self.logger.error(f"Clothing validation error: {str(e)}")
            return False
    
    def extract_product_name(self, soup):
        """Extract product name from AliExpress"""
        try:
            # Method 1: From meta tag
            title_meta = soup.find('meta', {'property': 'og:title'})
            if title_meta:
                name = self.sanitize_input(title_meta.get('content', ''))
                if name and '- AliExpress' in name:
                    name = name.split('- AliExpress')[0].strip()
                if name:
                    return name
            
            # Method 2: From JSON data
            json_data = self.extract_json_data(soup)
            if json_data and 'name' in json_data:
                name = self.sanitize_input(json_data['name'])
                if name and name != 'ItemDetailResp':
                    return name
            
            # Method 3: From title tag
            title_tag = soup.find('title')
            if title_tag:
                name = self.sanitize_input(title_tag.get_text())
                if name and '- AliExpress' in name:
                    name = name.split('- AliExpress')[0].strip()
                if name:
                    return name
            
            return "Product name not found"
            
        except Exception as e:
            self.logger.error(f"Product name extraction error: {str(e)}")
            return "Product name not found"
    
    def transform_aliexpress_image_url(self, url):
        """Transform AliExpress image URL to high resolution"""
        if not url:
            return url
        
        # Ensure URL has protocol
        if url.startswith('//'):
            url = 'https:' + url
        elif not url.startswith('http'):
            url = 'https://' + url
        
        # Remove thumbnail size suffixes and get full resolution
        patterns = [
            (r'_\d+x\d+\.jpg', '.jpg'),
            (r'_\d+x\d+\.png', '.png'),
            (r'_\d+x\d+\.webp', '.webp'),
            (r'_\d+x\d+q\d+\.jpg', '.jpg'),
            (r'\.jpg_\d+x\d+\.jpg', '.jpg'),
            (r'\.png_\d+x\d+\.png', '.png')
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, url):
                url = re.sub(pattern, replacement, url)
                break
        
        return url
    
    def extract_images(self, soup):
        """Extract at least 5 product images from AliExpress"""
        images = []
        seen_urls = set()
        
        try:
            # Method 1: From JSON data (most reliable)
            json_data = self.extract_json_data(soup)
            if json_data:
                # Try imagePathList first
                if 'imagePathList' in json_data:
                    for img_url in json_data['imagePathList'][:10]:
                        if img_url:
                            img_url = self.transform_aliexpress_image_url(img_url)
                            if img_url not in seen_urls:
                                images.append(img_url)
                                seen_urls.add(img_url)
                
                # Try summImagePathList if not enough images
                if len(images) < 5 and 'summImagePathList' in json_data:
                    for img_url in json_data['summImagePathList'][:10]:
                        if img_url:
                            img_url = self.transform_aliexpress_image_url(img_url)
                            if img_url not in seen_urls:
                                images.append(img_url)
                                seen_urls.add(img_url)
            
            # Method 2: From meta tags
            if len(images) < 5:
                og_images = soup.find_all('meta', {'property': 'og:image'})
                for og_image in og_images:
                    if len(images) >= 10:
                        break
                    img_url = og_image.get('content', '')
                    if img_url:
                        img_url = self.transform_aliexpress_image_url(img_url)
                        if img_url not in seen_urls:
                            images.append(img_url)
                            seen_urls.add(img_url)
            
            self.safe_log(f"Extracted {len(images)} AliExpress images")
            return images[:5]
            
        except Exception as e:
            self.logger.error(f"Image extraction error: {str(e)}")
            return []
    
    def scrape(self, url):
        """Main method to scrape AliExpress product - only platform, name, and images"""
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
            
            print(f"Clothing product validated on AliExpress! Proceeding with scraping...")
            
            product_data = {
                'platform': self.platform,
                'name': self.extract_product_name(soup),
                'images': self.extract_images(soup),
                'scraped_at': datetime.now().isoformat()
            }
            
            self.safe_log(f"Product data extracted successfully from AliExpress")
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error in AliExpress scraping: {str(e)}")
            print(f"Error: {str(e)}")
            return None
