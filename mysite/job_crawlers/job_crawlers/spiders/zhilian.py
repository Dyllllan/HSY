import scrapy
import json
import mysql.connector
from datetime import datetime
import os
import sys
import django

# Setup Django - add parent directory to path and configure Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local.settings.dev')
django.setup()

from wagtail.models import Page
from jobs.models import JobPage, JobIndexPage

class ZhilianSpider(scrapy.Spider):
    name = 'zhilian'
    allowed_domains = ['api.zhilian.com']
    
    def start_requests(self):
        # 示例API（需根据智联实际接口调整）
        keywords = ['Python实习生', 'Java应届']
        for kw in keywords:
            url = f'https://api.zhilian.com/v1/jobs?keyword={kw}&city=101010100'
            yield scrapy.Request(url, callback=self.parse_list, meta={'keyword': kw})
    
    def parse_list(self, response):
        data = json.loads(response.text)
        for job in data.get('data', []):
            # 关键：去重检查
            if not self.job_exists(job['id']):
                detail_url = f"https://api.zhilian.com/v1/job/{job['id']}"
                yield scrapy.Request(detail_url, callback=self.parse_detail)
        
        # 翻页逻辑（如果有）
        # ...
    
    def parse_detail(self, response):
        job_data = json.loads(response.text)['data']
        
        # **核心：将抓取的数据转换为Wagtail页面**
        # 1. 找到或创建索引页作为父页面
        parent_page = JobIndexPage.objects.filter(slug='zhilian-jobs').first()
        if not parent_page:
            # 如果不存在，可以创建一个或指定默认父页面
            parent_page = Page.objects.get(title='所有职位')
        
        # 2. 创建JobPage实例（注意：这不是保存到数据库，而是内存对象）
        job_page = JobPage(
            title = job_data['company']['name'] + "-" + job_data['jobName'],
            job_title = job_data['jobName'],
            company_name = job_data['company']['name'],
            location = job_data['city']['display'],
            salary = job_data['salary'],
            description = job_data['jobDesc'],  # 可能需要清理HTML
            job_type = self.map_job_type(job_data['jobType']),
            source_website = '智联招聘',
            source_url = job_data['pageUrl'],
            first_published_at = datetime.strptime(job_data['publishDate'], '%Y-%m-%d')
        )
        
        # 3. 添加到页面树并发布
        parent_page.add_child(instance=job_page)
        job_page.save_revision().publish()
        
        self.logger.info(f"已添加职位：{job_page.job_title}")
    
    def job_exists(self, source_id):
        return JobPage.objects.filter(source_url__contains=source_id).exists()
    
    def map_job_type(self, zhilian_type):
        type_map = {'0001': 'fulltime', '0002': 'intern', '0003': 'parttime'}
        return type_map.get(zhilian_type, 'fulltime')
