"""
检查 Wagtail Site 配置
使用方法: python manage.py check_wagtail_site
"""
from django.core.management.base import BaseCommand
from wagtail.models import Site, Page
from jobs.models import JobPage


class Command(BaseCommand):
    help = '检查 Wagtail Site 配置'

    def handle(self, *args, **options):
        # 检查站点配置
        sites = Site.objects.all()
        
        self.stdout.write(f'\n找到 {sites.count()} 个站点配置:')
        for site in sites:
            self.stdout.write(f'\n站点: {site.site_name}')
            self.stdout.write(f'  Hostname: {site.hostname}')
            self.stdout.write(f'  Port: {site.port}')
            self.stdout.write(f'  根页面: {site.root_page.title} (ID: {site.root_page.id})')
            self.stdout.write(f'  根页面 URL路径: {site.root_page.url_path}')
            self.stdout.write(f'  是否默认站点: {site.is_default_site}')
        
        # 检查一个示例职位页面
        job = JobPage.objects.filter(slug='java-44').first()
        if job:
            self.stdout.write(f'\n示例职位页面:')
            self.stdout.write(f'  标题: {job.title}')
            self.stdout.write(f'  URL路径: {job.url_path}')
            self.stdout.write(f'  URL: {job.url}')
            
            # 尝试获取完整 URL
            try:
                site = Site.find_for_request(None)
                if site:
                    full_url = f"http://{site.hostname}:{site.port or 80}{job.url_path}"
                    self.stdout.write(f'  完整URL: {full_url}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  获取完整URL时出错: {str(e)}'))
