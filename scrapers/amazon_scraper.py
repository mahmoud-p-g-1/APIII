from base_scraper import BaseScraper
from urllib.parse import urlparse
import hashlib
from datetime import datetime
import re

class AmazonScraper(BaseScraper):
    """Amazon-specific scraper class"""
    
    def __init__(self):
        super().__init__()
        self.platform = 'amazon'
        self.allowed_domains = ['amazon.com', 'www.amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de']
        
        # Add forbidden underwear keywords
        self.forbidden_keywords = [
            'underwear', 'bra', 'panties', 'boxers', 'briefs', 'lingerie',
            'thong', 'g-string', 'corset', 'bustier', 'negligee', 'chemise',
            'teddy', 'bodysuit', 'shapewear', 'pantyhose', 'stockings',
            'garter', 'intimate', 'undergarment', 'brassiere', 'camisole'
        ]
    
    def validate_url(self, url):
        """Security: Amazon URL validation"""
        try:
            parsed = urlparse(url)
            
            if parsed.netloc.lower() not in self.allowed_domains:
                self.logger.error(f"Invalid domain: {parsed.netloc}")
                return False, "Only Amazon domains are allowed"
            
            if parsed.scheme.lower() not in ['http', 'https']:
                self.logger.error(f"Invalid URL scheme: {parsed.scheme}")
                return False, "Only HTTP/HTTPS protocols are allowed"
            
            if len(url) > 2048:
                self.logger.error("URL too long")
                return False, "URL exceeds maximum length"
            
            if '/dp/' not in url and '/gp/product/' not in url:
                self.logger.error("Invalid Amazon product URL format")
                return False, "Invalid Amazon product URL format"
            
            return True, "URL is valid"
            
        except Exception as e:
            self.logger.error(f"URL validation error: {str(e)}")
            return False, f"URL validation failed: {str(e)}"
    
    def is_clothing_product(self, soup, url):
        """Validate if the Amazon product is clothing-related (excluding underwear)"""
        try:
            self.logger.info(f"Validating clothing product on Amazon...")
            
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
                'speaker', 'charger', 'cable', 'battery', 'automotive', 'car'
            ]
            
            for indicator in non_clothing_url_indicators:
                if indicator in url_lower:
                    self.logger.warning(f"Found NON-CLOTHING indicator '{indicator}' in URL - REJECTING")
                    return False
            
            # Check title
            title_element = soup.select_one('#productTitle')
            if title_element:
                title = self.sanitize_input(title_element.get_text().lower().strip())
                self.logger.info(f"Found title: {title[:100]}...")
                
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
                    'gown', 'suit', 'vest', 'outerwear'
                ]
                
                for keyword in allowed_clothing_keywords:
                    if keyword in title:
                        self.logger.info(f"Found allowed clothing keyword '{keyword}' in title")
                        return True
            
            # Check breadcrumbs
            breadcrumbs = soup.select('#wayfinding-breadcrumbs_feature_div a')
            
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
                    'pants', 'women', 'men', 'shoes'
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
        """Extract product name from Amazon"""
        selectors = ['#productTitle', '.product-title', 'h1.a-size-large', 'span#productTitle']
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    name = self.sanitize_input(element.get_text().strip())
                    if name:
                        return name
            except Exception:
                continue
        
        return "Product name not found"
    
    def transform_amazon_image_urls(self, images):
        """Transform Amazon image URLs to high resolution AFTER extraction"""
        transformed_images = []
        
        for url in images:
            if not url:
                continue
            
            # Check if this is an Amazon image URL
            if '/images/I/' in url or '/images/i/' in url:
                try:
                    # Extract everything after /images/I/ or /images/i/
                    if '/images/I/' in url:
                        parts = url.split('/images/I/')
                    else:
                        parts = url.split('/images/i/')
                    
                    base_url = parts[0]
                    image_part = parts[1]
                    
                    # Extract the image ID (everything before the first . or _)
                    # Using a more flexible pattern
                    image_id = re.split(r'[._]', image_part)[0]
                    
                    if image_id:
                        # Create the high resolution URL with your exact format
                        high_res_url = f"{base_url}/images/I/{image_id}._AC_SL1900_QL100_FMwebp_.jpg"
                        transformed_images.append(high_res_url)
                        self.logger.info(f"Transformed image: {image_id} to high resolution")
                    else:
                        # If we can't extract ID, keep original
                        transformed_images.append(url)
                        self.logger.warning(f"Could not extract image ID from URL")
                except Exception as e:
                    # If any error occurs, keep the original URL
                    transformed_images.append(url)
                    self.logger.error(f"Error transforming URL: {str(e)}")
            else:
                # Not an Amazon image URL, keep as is
                transformed_images.append(url)
                self.logger.warning(f"Not an Amazon image URL format")
        
        return transformed_images

    def extract_images(self, soup):
        """Extract product images from Amazon - RAW URLs without transformation"""
        images = []
        seen_urls = set()
        
        try:
            # Method 1: Main product image
            main_image = soup.select_one('#landingImage')
            if main_image and main_image.get('src'):
                img_url = main_image['src']
                if self.is_valid_image_url(img_url) and img_url not in seen_urls:
                    images.append(img_url)
                    seen_urls.add(img_url)
            
            # Method 2: Thumbnail images
            thumb_images = soup.select('.imageThumbnail img')
            for img in thumb_images:
                if len(images) >= 10:
                    break
                img_url = img.get('src', '')
                if img_url and self.is_valid_image_url(img_url) and img_url not in seen_urls:
                    images.append(img_url)
                    seen_urls.add(img_url)
            
            # Method 3: Alternative images from data attributes
            alt_images = soup.select('[data-old-hires]')
            for img in alt_images:
                if len(images) >= 10:
                    break
                img_url = img.get('data-old-hires', '')
                if img_url and self.is_valid_image_url(img_url) and img_url not in seen_urls:
                    images.append(img_url)
                    seen_urls.add(img_url)
            
            # Method 4: Color variant images
            variant_images = soup.select('.imgSwatch')
            for img in variant_images:
                if len(images) >= 10:
                    break
                img_url = img.get('src', '')
                if img_url and self.is_valid_image_url(img_url) and img_url not in seen_urls:
                    images.append(img_url)
                    seen_urls.add(img_url)
            
            # Method 5: Extract from JavaScript
            scripts = soup.find_all('script', type='text/javascript')
            for script in scripts:
                if len(images) >= 10:
                    break
                if script.string and 'ImageBlockATF' in script.string:
                    urls = re.findall(r'"hiRes":"([^"]+)"', script.string)
                    for url in urls:
                        if len(images) >= 10:
                            break
                        decoded_url = url.replace('\\/', '/')
                        if self.is_valid_image_url(decoded_url) and decoded_url not in seen_urls:
                            images.append(decoded_url)
                            seen_urls.add(decoded_url)
            
            self.logger.info(f"Extracted {len(images)} raw Amazon images")
            
            # Take first 5 images
            raw_images = images[:5]
            
            # NOW TRANSFORM THE URLS AFTER EXTRACTION
            transformed_images = self.transform_amazon_image_urls(raw_images)
            
            return transformed_images
            
        except Exception as e:
            self.logger.error(f"Amazon image extraction error: {str(e)}")
            return []
    
    def is_valid_image_url(self, url):
        """Validate Amazon image URLs"""
        try:
            if not url or not isinstance(url, str):
                return False
            
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            amazon_image_domains = ['m.media-amazon.com', 'images-amazon.com', 'media-amazon.com']
            if not any(domain in parsed.netloc for domain in amazon_image_domains):
                return False
            
            if url.lower().endswith('.gif'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def scrape(self, url):
        """Main method to scrape Amazon product - only platform, name, and images"""
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
            
            print(f"Clothing product validated on Amazon! Proceeding with scraping...")
            
            product_data = {
                'platform': self.platform,
                'name': self.extract_product_name(soup),
                'images': self.extract_images(soup),  # This now returns transformed URLs
                'scraped_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Product data extracted successfully from Amazon")
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error in Amazon scraping: {str(e)}")
            print(f"Error: {str(e)}")
            return None
