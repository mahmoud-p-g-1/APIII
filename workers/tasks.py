import threading
import time
from queue_manager import queue_manager
from firebase_config import update_job_status
from scrapers import AmazonScraper, AlibabaScraper, AliExpressScraper, EbayScraper, HMScraper
from config import Config
import requests

def process_scraping_job(job_data):
    """Process a single scraping job"""
    try:
        job_id = job_data['job_id']
        user_id = job_data['user_id']
        url = job_data['url']
        platform = job_data['platform']
        
        # Update status to processing
        update_job_status(user_id, job_id, 'processing')
        
        # Select appropriate scraper
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
            raise ValueError("Unsupported platform")
        
        # Perform scraping
        result = scraper.scrape(url)
        
        if result:
            # Update status to completed
            update_job_status(user_id, job_id, 'completed', result)
            return result
        else:
            # Check if it's a 404
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 404:
                    raise Exception("Product No Longer Available")
            except:
                pass
            
            raise Exception("Failed to scrape product")
            
    except Exception as e:
        error_message = str(e)
        
        # Check for specific error types
        if '404' in error_message:
            error_message = "Product No Longer Available"
        elif any(x in error_message.lower() for x in ['dangerous', 'exploit', 'rce']):
            error_message = "URL from Dangerous Site"
        elif 'invalid' in error_message.lower():
            error_message = "Unsupported URL Format"
        
        update_job_status(user_id, job_id, 'failed', {'error': error_message})
        return None

def worker_thread():
    """Worker thread that processes jobs from queue"""
    print(f"Worker thread started")
    
    while True:
        try:
            # Get job from queue
            job_data = queue_manager.get_job(timeout=1)
            
            if job_data:
                print(f"Processing job: {job_data['job_id']}")
                process_scraping_job(job_data)
            else:
                # No job available, wait a bit
                time.sleep(1)
                
        except Exception as e:
            print(f"Worker error: {str(e)}")
            time.sleep(1)

def start_worker_threads():
    """Start multiple worker threads"""
    num_workers = Config.WORKER_THREADS
    
    for i in range(num_workers):
        thread = threading.Thread(target=worker_thread, daemon=True)
        thread.start()
        print(f"Started worker thread {i+1}/{num_workers}")
