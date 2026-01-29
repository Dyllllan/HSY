"""
检查 JobIndexPage 的状态和位置
使用方法: python manage.py check_job_index
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from jobs.models import JobIndexPage


class Command(BaseCommand):
    help = '检查 JobIndexPage 的状态'

    def handle(self, *args, **options):
        # 查找所有 JobIndexPage
        job_index_pages = JobIndexPage.objects.all()
        
        if not job_index_pages.exists():
            self.stdout.write(self.style.WARNING('\n[WARNING] 未找到任何 JobIndexPage'))
            return
        
        # 获取 Site 的 root_page
        default_site = Site.objects.filter(is_default_site=True).first()
        if default_site:
            root_page = default_site.root_page
            self.stdout.write(f'\nSite root_page: {root_page.title} (ID: {root_page.id})')
            self.stdout.write(f'  URL路径: {root_page.url_path}')
        else:
            root_page = None
            self.stdout.write('\n[WARNING] 未找到默认站点')
        
        self.stdout.write(f'\n找到 {job_index_pages.count()} 个 JobIndexPage:')
        
        for idx, job_index in enumerate(job_index_pages, 1):
            self.stdout.write(f'\n[{idx}] {job_index.title}')
            self.stdout.write(f'  ID: {job_index.id}')
            self.stdout.write(f'  Slug: {job_index.slug}')
            self.stdout.write(f'  URL路径: {job_index.url_path}')
            self.stdout.write(f'  深度: {job_index.depth}')
            self.stdout.write(f'  是否发布: {"是" if job_index.live else "否"}')
            
            parent = job_index.get_parent()
            if parent:
                self.stdout.write(f'  父页面: {parent.title} (ID: {parent.id})')
                self.stdout.write(f'    路径: {parent.path}')
                self.stdout.write(f'    URL路径: {parent.url_path}')
                self.stdout.write(f'    深度: {parent.depth}')
                
                # 检查是否在根页面下
                if root_page and parent.id == root_page.id:
                    self.stdout.write(self.style.SUCCESS('  [OK] 在 Site.root_page 下'))
                else:
                    self.stdout.write(self.style.WARNING('  [WARNING] 不在 Site.root_page 下'))
            else:
                self.stdout.write(self.style.ERROR('  [ERROR] 没有父页面'))
            
            # 检查子页面数量
            children_count = job_index.get_children().count()
            self.stdout.write(f'  子页面数量: {children_count}')
            
            # 检查是否有 slug='jobs' 的页面
            if job_index.slug == 'jobs':
                self.stdout.write(self.style.SUCCESS('  [OK] Slug 为 "jobs"'))
            else:
                self.stdout.write(self.style.WARNING(f'  [WARNING] Slug 为 "{job_index.slug}"，不是 "jobs"'))
