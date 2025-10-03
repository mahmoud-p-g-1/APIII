# workers/scraping_worker.py

import os
import sys
import threading
import time
from datetime import datetime
import traceback

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from queue_manager import queue_manager
from firebase_config import get_access_token
import requests

# Import scrapers
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scrapers'))

from amazon_scraper import AmazonScraper
from aliexpress_scraper import AliExpressScraper
from ebay_scraper import EbayScraper
from alibaba_scraper import AlibabaScraper
from hm_scraper import HMScraper

FIREBASE_PROJECT_ID = "fitmatch-1"

def get_scraper_for_platform(platform):
    """Get appropriate scraper for platform"""
    scrapers = {
        'amazon': AmazonScraper,
        'aliexpress': AliExpressScraper,
        'ebay': EbayScraper,
        'alibaba': AlibabaScraper,
        'hm': HMScraper
    }
    
    scraper_class = scrapers.get(platform.lower())
    if scraper_class:
        return scraper_class()
    else:
        raise ValueError(f"Unsupported platform: {platform}")

def update_scraping_job_status(job_id, status, result_data=None):
    """Update scraping job status in Firestore"""
    try:
        print(f"\n[FIRESTORE] Updating scraping job status to: {status}")
        
        token = get_access_token()
        if not token:
            print("[FIRESTORE] WARNING: No Firebase token available")
            return False
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        job_data = {
            'fields': {
                'status': {'stringValue': status},
                'updated_at': {'stringValue': datetime.now().isoformat()},
                'job_type': {'stringValue': 'scraping'}
            }
        }
        
        if result_data:
            if status == 'completed':
                job_data['fields']['completed_at'] = {'stringValue': datetime.now().isoformat()}
                
                # Store scraping results
                if 'platform' in result_data:
                    job_data['fields']['platform'] = {'stringValue': result_data['platform']}
                
                if 'name' in result_data:
                    job_data['fields']['product_name'] = {'stringValue': result_data['name']}
                
                if 'images' in result_data:
                    job_data['fields']['images'] = {'stringValue': str(result_data['images'])}
                
                if 'scraped_at' in result_data:
                    job_data['fields']['scraped_at'] = {'stringValue': result_data['scraped_at']}
                    
            elif status == 'failed':
                job_data['fields']['failed_at'] = {'stringValue': datetime.now().isoformat()}
                if 'error' in result_data:
                    job_data['fields']['error'] = {'stringValue': str(result_data['error'])}
        
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/scraping_jobs/{job_id}"
        response = requests.patch(url, json=job_data, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"[FIRESTORE] ✓ Scraping job status updated successfully")
            return True
        else:
            print(f"[FIRESTORE] ✗ Failed to update status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FIRESTORE] ✗ Error: {e}")
        return False

def process_scraping_job(job_data):
    """Process scraping job"""
    job_id = job_data['job_id']
    user_id = job_data['user_id']
    url = job_data['url']
    platform = job_data['platform']
    
    print(f"\n{'='*80}")
    print(f"[SCRAPING PROCESSING] Starting Job: {job_id}")
    print(f"[SCRAPING PROCESSING] User: {user_id}")
    print(f"[SCRAPING PROCESSING] Platform: {platform}")
    print(f"[SCRAPING PROCESSING] URL: {url[:50]}...")
    print(f"[SCRAPING PROCESSING] Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*80}")
    
    try:
        # Update status to processing
        update_scraping_job_status(job_id, 'processing')
        
        # Get appropriate scraper
        scraper = get_scraper_for_platform(platform)
        
        # Perform scraping
        print(f"[SCRAPING] Starting scraping with {platform} scraper...")
        result = scraper.scrape(url)
        
        if result:
            print(f"[SCRAPING] ✓ Successfully scraped product:")
            print(f"  Platform: {result.get('platform')}")
            print(f"  Name: {result.get('name', 'N/A')[:50]}...")
            print(f"  Images: {len(result.get('images', []))} found")
            
            # Update job status to completed
            update_scraping_job_status(job_id, 'completed', result)
            
            # SAVE TO FIRESTORE - ADD THIS SECTION
            try:
                from firebase_config import save_scraping_to_firestore, update_job_status
                import_id = save_scraping_to_firestore(user_id, result, url)
                if import_id:
                    print(f"[FIRESTORE] ✓ Saved to Firestore with ID: {import_id}")
                    
                    # Update the job with the import ID
                    update_job_status(user_id, job_id, 'completed', {
                        **result,
                        'importId': import_id  # ADD THIS LINE
                    })
                else:
                    print(f"[FIRESTORE] ✗ Failed to save to Firestore")
            except Exception as e:
                print(f"[FIRESTORE] ✗ Error saving to Firestore: {str(e)}")
            
            print(f"\n{'='*80}")
            print(f"[SUCCESS] Scraping job {job_id} completed!")
            print(f"[SUCCESS] Platform: {platform}")
            print(f"[SUCCESS] Product: {result.get('name', 'N/A')[:50]}...")
            print(f"[SUCCESS] Images: {len(result.get('images', []))}")
            print(f"{'='*80}")
            
        else:
            raise Exception("Scraping returned no results")
        
    except Exception as e:
        print(f"[SCRAPING ERROR] {str(e)}")
        print(f"[SCRAPING ERROR] Traceback: {traceback.format_exc()}")
        
        update_scraping_job_status(job_id, 'failed', {'error': str(e)})
        
def scraping_worker_thread():
    """Worker thread for scraping jobs"""
    print(f"\n{'='*80}")
    print(f"[SCRAPING WORKER] Scraping Worker Initialized")
    print(f"[SCRAPING WORKER] Supported platforms: Amazon, AliExpress, eBay, Alibaba, H&M")
    print(f"[SCRAPING WORKER] ScrapingBee integration: Available")
    print(f"[SCRAPING WORKER] Waiting for scraping jobs...")
    print(f"{'='*80}\n")
    
    while True:
        try:
            queue_size = queue_manager.get_queue_size()
            if queue_size > 0:
                job = queue_manager.get_job(timeout=0.5)
                if job:
                    job_type = job.get('type', 'unknown')
                    job_id = job.get('job_id', 'unknown')
                    
                    print(f"[SCRAPING QUEUE] Retrieved job: {job_id} (type: {job_type})")
                    
                    if job_type == 'scraping':
                        process_scraping_job(job)
                    else:
                        print(f"[SCRAPING QUEUE] Not a scraping job, returning to queue")
                        queue_manager.add_job(job)
            
        except Exception as e:
            if str(e):
                print(f"[SCRAPING WORKER ERROR] {e}")
        
        time.sleep(0.5)

def start_scraping_worker():
    """Start scraping worker thread"""
    thread = threading.Thread(target=scraping_worker_thread, daemon=True)
    thread.start()
    print("[SCRAPING WORKER] Scraping worker thread started")
    return thread
