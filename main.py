import json
from datetime import datetime
from scrapers import AmazonScraper, AlibabaScraper, AliExpressScraper, EbayScraper, HMScraper
from urllib.parse import urlparse

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
        return 'unknown'

def scrape_product(url):
    """Main function to scrape a product from any supported platform"""
    platform = detect_platform(url)
    
    print(f"\n{'='*80}")
    print(f"Starting scraping process...")
    print(f"Detected platform: {platform.upper()}")
    print(f"URL: {url[:60]}...")
    print(f"{'='*80}")
    
    if platform == 'amazon':
        scraper = AmazonScraper()
    elif platform == 'alibaba':
        scraper = AlibabaScraper()
    elif platform == 'aliexpress':
        scraper = AliExpressScraper()
    elif platform == 'ebay':
        scraper = EbayScraper()
    elif platform == 'hm':
        scraper = HMScraper()
    else:
        print(f"Error: Unsupported platform: {platform}")
        return None
    
    product_data = scraper.scrape(url)
    
    if product_data:
        display_product_data(product_data)
        save_product_data(product_data)
        return product_data
    else:
        print("Failed to scrape product data")
        return None

def display_product_data(product_data):
    """Display scraped product data in a formatted way"""
    platform = product_data['platform'].upper()
    print(f"\n{platform} PRODUCT DATA")
    print("="*50)
    
    print(f"\n**Platform:** {product_data['platform']}")
    print(f"**Product Name:** {product_data['name']}")
    print(f"**Scraped At:** {product_data['scraped_at']}")
    
    print(f"\n**Images Found:** {len(product_data['images'])}")
    if product_data['images']:
        print("**High-Resolution Image URLs:**")
        for i, img_url in enumerate(product_data['images'], 1):
            print(f"  {i}. {img_url}")

def save_product_data(product_data):
    """Save product data to a JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{product_data['platform']}_product_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(product_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n**Data saved to:** {filename}")
    print(f"{product_data['platform'].upper()} scraping completed!")

def main():
    """Main function to run the scraper"""
    test_urls = [
        # H&M URL
        "https://www2.hm.com/en_us/productpage.1289684010.html",
        
        # Amazon URL
        # "https://www.amazon.com/French-Toast-Little-Sleeve-Collar/dp/B01N3M8S0K",
        
        # eBay URL
        # "https://www.ebay.com/itm/357600968365",
        
        # Alibaba URL
        # "https://www.alibaba.com/product-detail/Women-s-Sexy-One-Shoulder-Cut_1601536747208.html",
        
        # AliExpress URL
        # "https://www.aliexpress.us/item/3256808842649818.html"
    ]
    
    for url in test_urls:
        try:
            scrape_product(url)
            print("\n" + "="*80 + "\n")
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            continue

if __name__ == "__main__":
    main()
