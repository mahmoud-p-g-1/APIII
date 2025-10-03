# scrapers/__init__.py
from .base_scraper import BaseScraper
from .amazon_scraper import AmazonScraper
from .aliexpress_scraper import AliExpressScraper
from .ebay_scraper import EbayScraper

__all__ = ['BaseScraper', 'AmazonScraper', 'AliExpressScraper', 'EbayScraper']
