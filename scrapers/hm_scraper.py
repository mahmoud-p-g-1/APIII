from base_scraper import BaseScraper
from urllib.parse import urlparse
import hashlib
from datetime import datetime
import re
import json

class HMScraper(BaseScraper):
    """H&M-specific scraper class"""
    
    def __init__(self):
        super().__init__()
        self.platform = 'hm'
        self.allowed_domains = [
            'hm.com', 'www.hm.com', 'www2.hm.com',
            'm.hm.com', 'www.hm.com'
        ]
        
        # Add forbidden underwear keywords
        self.forbidden_keywords = [
            'underwear', 'bra', 'panties', 'boxers', 'briefs', 'lingerie',
            'thong', 'g-string', 'corset', 'bustier', 'negligee', 'chemise',
            'teddy', 'bodysuit', 'shapewear', 'pantyhose', 'stockings',
            'garter', 'intimate', 'undergarment', 'brassiere', 'camisole',
            'slip', 'girdle', 'foundation garment', 'bralette', 'boxer briefs'
        ]
    
    def validate_url(self, url):
        """Security: H&M URL validation"""
        try:
            parsed = urlparse(url)
            
            domain_valid = False
            for allowed_domain in self.allowed_domains:
                if parsed.netloc.lower() == allowed_domain or parsed.netloc.lower().endswith('.' + allowed_domain):
                    domain_valid = True
                    break
            
            if not domain_valid:
                self.logger.error(f"Invalid domain: {parsed.netloc}")
                return False, "Only H&M domains are allowed"
            
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
            
            # Check for H&M product URL patterns
            if not any(pattern in url for pattern in ['productpage', '/product/', '.html']):
                self.logger.error("Invalid H&M product URL format")
                return False, "Invalid H&M product URL format"
            
            return True, "URL is valid"
            
        except Exception as e:
            self.logger.error(f"URL validation error: {str(e)}")
            return False, f"URL validation failed: {str(e)}"
    
    def is_clothing_product(self, soup, url):
        """Validate if the H&M product is clothing-related (excluding underwear)"""
        try:
            self.logger.info(f"Validating clothing product on H&M...")
            
            url_lower = url.lower()
            
            # Check for FORBIDDEN underwear keywords in URL
            for keyword in self.forbidden_keywords:
                if keyword in url_lower:
                    self.logger.warning(f"Found FORBIDDEN underwear keyword '{keyword}' in URL - REJECTING")
                    return False
            
            # Check for NON-CLOTHING indicators in URL
            non_clothing_url_indicators = [
                'home-decor', 'home-textiles', 'beauty', 'cosmetics', 'makeup',
                'fragrance', 'candles', 'accessories-only', 'jewelry', 'watches',
                'bags-only', 'home', 'kitchen', 'bathroom', 'bedroom'
            ]
            
            for indicator in non_clothing_url_indicators:
                if indicator in url_lower:
                    self.logger.warning(f"Found NON-CLOTHING indicator '{indicator}' in URL - REJECTING")
                    return False
            
            # Check title from meta tags or h1
            title = ""
            
            # Try meta property og:title first
            title_meta = soup.find('meta', {'property': 'og:title'})
            if title_meta:
                title = self.sanitize_input(title_meta.get('content', '').lower())
            
            # Try regular title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = self.sanitize_input(title_tag.get_text().lower())
            
            # Try h1 tags
            if not title:
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = self.sanitize_input(h1_tag.get_text().lower())
            
            if title:
                self.logger.info(f"Found title: {title[:100]}...")
                
                # Check for FORBIDDEN underwear keywords in title
                for keyword in self.forbidden_keywords:
                    if keyword in title:
                        self.logger.warning(f"Found FORBIDDEN underwear keyword '{keyword}' in title - REJECTING")
                        return False
                
                # Check for NON-CLOTHING keywords
                non_clothing_title_keywords = [
                    'candle', 'diffuser', 'fragrance', 'perfume', 'makeup',
                    'cosmetic', 'beauty', 'home decor', 'cushion', 'pillow',
                    'duvet', 'towel', 'bath mat', 'shower curtain', 'lamp',
                    'vase', 'mirror', 'storage', 'basket', 'box'
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
                    'gown', 'suit', 'vest', 'outerwear', 'knitwear', 'sweatshirt',
                    'pullover', 'jumper', 'tunic', 'polo', 'henley'
                ]
                
                for keyword in allowed_clothing_keywords:
                    if keyword in title:
                        self.logger.info(f"Found allowed clothing keyword '{keyword}' in title")
                        return True
            
            # Check structured data (JSON-LD)
            json_ld = soup.find('script', {'type': 'application/ld+json', 'id': 'product-schema'})
            if json_ld:
                try:
                    data = json.loads(json_ld.string)
                    if 'category' in data:
                        category = str(data['category'].get('name', '')).lower()
                        
                        # Check for forbidden categories
                        for keyword in self.forbidden_keywords:
                            if keyword in category:
                                self.logger.warning(f"Found FORBIDDEN category: {category}")
                                return False
                        
                        # Check for allowed categories
                        allowed_categories = [
                            'cardigan', 'sweater', 'shirt', 'dress', 'pants',
                            'jeans', 'jacket', 'coat', 'skirt', 'top', 'blouse'
                        ]
                        
                        for allowed in allowed_categories:
                            if allowed in category:
                                self.logger.info(f"Found allowed category: {category}")
                                return True
                    
                    if 'description' in data:
                        description = str(data['description']).lower()
                        
                        # Check description for underwear keywords
                        for keyword in self.forbidden_keywords:
                            if keyword in description:
                                self.logger.warning(f"Found FORBIDDEN keyword in description")
                                return False
                        
                        # Check for clothing indicators
                        for keyword in allowed_clothing_keywords:
                            if keyword in description:
                                self.logger.info(f"Found clothing keyword in description")
                                return True
                
                except Exception as e:
                    self.logger.warning(f"Error parsing JSON-LD: {str(e)}")
            
            # Check breadcrumbs
            breadcrumb_json = soup.find('script', {'type': 'application/ld+json', 'id': 'breadcrumb-schema'})
            if breadcrumb_json:
                try:
                    breadcrumb_data = json.loads(breadcrumb_json.string)
                    if 'itemListElement' in breadcrumb_data:
                        for item in breadcrumb_data['itemListElement']:
                            item_name = str(item.get('name', '')).lower()
                            
                            # Check for underwear in breadcrumbs
                            for keyword in self.forbidden_keywords:
                                if keyword in item_name:
                                    self.logger.warning(f"Found FORBIDDEN keyword in breadcrumb: {item_name}")
                                    return False
                            
                            # Check for clothing categories
                            clothing_indicators = [
                                'women', 'men', 'clothing', 'sweater', 'cardigan',
                                'dress', 'shirt', 'pants', 'jacket', 'coat'
                            ]
                            
                            for indicator in clothing_indicators:
                                if indicator in item_name:
                                    self.logger.info(f"Found clothing indicator in breadcrumb: {item_name}")
                                    return True
                
                except Exception as e:
                    self.logger.warning(f"Error parsing breadcrumb JSON: {str(e)}")
            
            self.logger.warning("Product does not appear to be allowed clothing")
            return False
            
        except Exception as e:
            self.logger.error(f"Clothing validation error: {str(e)}")
            return False
    
    def extract_product_name(self, soup):
        """Extract product name from H&M"""
        try:
            # Method 1: From structured data
            json_ld = soup.find('script', {'type': 'application/ld+json', 'id': 'product-schema'})
            if json_ld:
                try:
                    data = json.loads(json_ld.string)
                    if 'name' in data:
                        name = self.sanitize_input(data['name'])
                        if name:
                            return name
                except:
                    pass
            
            # Method 2: From meta tags
            title_meta = soup.find('meta', {'property': 'og:title'})
            if title_meta:
                name = self.sanitize_input(title_meta.get('content', ''))
                # Remove H&M suffix
                name = re.sub(r'\s*\|\s*H&M.*$', '', name)
                if name:
                    return name
            
            # Method 3: From title tag
            title_tag = soup.find('title')
            if title_tag:
                name = self.sanitize_input(title_tag.get_text())
                # Remove H&M suffix
                name = re.sub(r'\s*\|\s*H&M.*$', '', name)
                if name:
                    return name
            
            # Method 4: From h1 tag
            h1_tag = soup.find('h1')
            if h1_tag:
                name = self.sanitize_input(h1_tag.get_text())
                if name:
                    return name
            
            return "Product name not found"
            
        except Exception as e:
            self.logger.error(f"Product name extraction error: {str(e)}")
            return "Product name not found"
    
    def transform_hm_image_url(self, url):
        """Transform H&M image URL to high resolution"""
        if not url:
            return url
        
        # H&M image URL patterns:
        # From: https://image.hm.com/assets/hm/...jpg?imwidth=256
        # To: https://image.hm.com/assets/hm/...jpg?imwidth=2160
        
        # Remove existing width parameter and set to maximum
        url = re.sub(r'\?imwidth=\d+', '?imwidth=2160', url)
        
        # If no width parameter exists, add it
        if '?imwidth=' not in url:
            if '?' in url:
                url += '&imwidth=2160'
            else:
                url += '?imwidth=2160'
        
        return url
    
    def extract_images(self, soup):
        """Extract at least 5 product images from H&M"""
        images = []
        seen_urls = set()
        
        try:
            # Method 1: From structured data
            json_ld = soup.find('script', {'type': 'application/ld+json', 'id': 'product-schema'})
            if json_ld:
                try:
                    data = json.loads(json_ld.string)
                    if 'image' in data:
                        for img_url in data['image'][:10]:  # Get more to ensure 5 good ones
                            if img_url:
                                # Transform to high resolution
                                img_url = self.transform_hm_image_url(img_url)
                                if self.is_valid_image_url(img_url) and img_url not in seen_urls:
                                    images.append(img_url)
                                    seen_urls.add(img_url)
                except:
                    pass
            
            # Method 2: From img tags with srcSet
            if len(images) < 5:
                img_tags = soup.find_all('img')
                for img in img_tags:
                    if len(images) >= 10:
                        break
                    
                    # Try srcSet first (contains multiple resolutions)
                    srcset = img.get('srcset', '')
                    if srcset:
                        # Extract the highest resolution URL from srcSet
                        urls = re.findall(r'(https://image\.hm\.com[^\s]+)', srcset)
                        if urls:
                            # Get the last one (usually highest resolution)
                            img_url = urls[-1]
                            img_url = self.transform_hm_image_url(img_url)
                            if self.is_valid_image_url(img_url) and img_url not in seen_urls:
                                images.append(img_url)
                                seen_urls.add(img_url)
                    
                    # Try regular src
                    src = img.get('src', '')
                    if src and 'image.hm.com' in src:
                        img_url = self.transform_hm_image_url(src)
                        if self.is_valid_image_url(img_url) and img_url not in seen_urls:
                            images.append(img_url)
                            seen_urls.add(img_url)
            
            # Method 3: From meta property og:image
            if len(images) < 5:
                og_image = soup.find('meta', {'property': 'og:image'})
                if og_image:
                    img_url = og_image.get('content', '')
                    if img_url:
                        img_url = self.transform_hm_image_url(img_url)
                        if self.is_valid_image_url(img_url) and img_url not in seen_urls:
                            images.append(img_url)
                            seen_urls.add(img_url)
            
            # Method 4: Look for data-testid="next-image" elements
            if len(images) < 5:
                next_images = soup.find_all('div', {'data-testid': 'next-image'})
                for div in next_images:
                    if len(images) >= 10:
                        break
                    img = div.find('img')
                    if img:
                        # Try srcSet
                        srcset = img.get('srcset', '')
                        if srcset:
                            urls = re.findall(r'(https://image\.hm\.com[^\s]+)', srcset)
                            if urls:
                                img_url = urls[-1]  # Get highest resolution
                                img_url = self.transform_hm_image_url(img_url)
                                if self.is_valid_image_url(img_url) and img_url not in seen_urls:
                                    images.append(img_url)
                                    seen_urls.add(img_url)
                        
                        # Try src
                        src = img.get('src', '')
                        if src and 'image.hm.com' in src:
                            img_url = self.transform_hm_image_url(src)
                            if self.is_valid_image_url(img_url) and img_url not in seen_urls:
                                images.append(img_url)
                                seen_urls.add(img_url)
            
            self.logger.info(f"Extracted {len(images)} H&M images")
            return images[:5]  # Return exactly 5 images
            
        except Exception as e:
            self.logger.error(f"H&M image extraction error: {str(e)}")
            return []
    
    def is_valid_image_url(self, url):
        """Validate H&M image URLs"""
        try:
            if not url or not isinstance(url, str):
                return False
            
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # H&M image domains
            hm_image_domains = [
                'image.hm.com', 'lp.hm.com', 'lp2.hm.com',
                'asset1.hm.com', 'asset2.hm.com'
            ]
            
            if not any(domain in parsed.netloc for domain in hm_image_domains):
                return False
            
            # Exclude GIF files
            if url.lower().endswith('.gif'):
                return False
            
            # Exclude placeholder/icon images
            excluded_patterns = [
                'placeholder', 'icon', 'logo', 'blank',
                'transparent', 'pixel', 'spacer'
            ]
            
            url_lower = url.lower()
            for pattern in excluded_patterns:
                if pattern in url_lower:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def scrape(self, url):
        """Main method to scrape H&M product - only platform, name, and images"""
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
            
            print(f"Clothing product validated on H&M! Proceeding with scraping...")
            
            product_data = {
                'platform': self.platform,
                'name': self.extract_product_name(soup),
                'images': self.extract_images(soup),
                'scraped_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Product data extracted successfully from H&M")
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error in H&M scraping: {str(e)}")
            print(f"Error: {str(e)}")
            return None
