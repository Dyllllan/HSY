from django.core.management.base import BaseCommand
from scrapy.cmdline import execute
import os
import sys

class Command(BaseCommand):
    help = 'Run job crawlers using Scrapy'

    def handle(self, *args, **options):
        # Change to the crawlers directory
        crawlers_dir = os.path.join(os.path.dirname(__file__), '../../../job_crawlers')
        os.chdir(crawlers_dir)
        
        # Run Scrapy crawler
        sys.argv = ['scrapy', 'crawl', 'zhilian']
        execute()