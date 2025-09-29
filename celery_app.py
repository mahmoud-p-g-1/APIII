from celery import Celery
from config import Config

celery_app = Celery(
    'scraping_api',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=['workers.tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60,  # 60 seconds max per task
    task_soft_time_limit=50,  # Soft limit at 50 seconds
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Rate limiting per platform
celery_app.conf.task_routes = {
    'workers.tasks.scrape_amazon': {'queue': 'amazon'},
    'workers.tasks.scrape_alibaba': {'queue': 'alibaba'},
    'workers.tasks.scrape_aliexpress': {'queue': 'aliexpress'},
    'workers.tasks.scrape_ebay': {'queue': 'ebay'},
    'workers.tasks.scrape_hm': {'queue': 'hm'},
}
