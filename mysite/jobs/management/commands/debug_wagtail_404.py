"""
调试 Wagtail 404 问题
使用方法: python manage.py debug_wagtail_404 --url-path /zhilian-jobs/python-3/
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from jobs.models import JobPage, JobIndexPage
from django.test import RequestFactory


class Command(BaseCommand):
    help = '调试 Wagtail 404 问题'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url-path',
            type=str,
            default='/zhilian-jobs/python-3/',
            help='要调试的 URL 路径',
        )

    def handle(self, *args, **options):
        url_path = options['url_path']
        
        self.stdout.write(f'\n{"="*80}')
        self.stdout.write(f'调试 URL 路径: {url_path}')
        self.stdout.write(f'{"="*80}\n')
        
        # 1. 检查页面是否存在
        page = Page.objects.filter(url_path=url_path).first()
        if not page:
            self.stdout.write(self.style.ERROR('✗ 页面不存在'))
            # 尝试查找相似的
            similar = Page.objects.filter(url_path__icontains=url_path.split('/')[-2]).first()
            if similar:
                self.stdout.write(f'  找到相似的路径: {similar.url_path}')
            return
        
        self.stdout.write(f'[OK] 找到页面: {page.title} (ID: {page.id})')
        self.stdout.write(f'  类型: {type(page.specific).__name__}')
        self.stdout.write(f'  已发布: {page.live}')
        self.stdout.write(f'  Path: {page.path}')
        self.stdout.write(f'  Depth: {page.depth}')
        self.stdout.write(f'  URL路径: {page.url_path}')
        
        # 2. 检查页面树结构
        self.stdout.write(f'\n页面树结构:')
        ancestors = page.get_ancestors()
        for ancestor in ancestors:
            indent = '  ' * (ancestor.depth - 1)
            self.stdout.write(f'{indent}- {ancestor.title} (ID: {ancestor.id}, slug: {ancestor.slug}, depth: {ancestor.depth})')
        self.stdout.write(f'  {"  " * (page.depth - 1)}-> {page.title} (ID: {page.id}, slug: {page.slug}, depth: {page.depth})')
        
        # 3. 检查 Site 配置
        self.stdout.write(f'\n站点配置:')
        sites = Site.objects.all()
        for site in sites:
            self.stdout.write(f'\n站点: {site.site_name}')
            self.stdout.write(f'  Hostname: {site.hostname}')
            self.stdout.write(f'  Port: {site.port}')
            self.stdout.write(f'  根页面: {site.root_page.title} (ID: {site.root_page.id})')
            self.stdout.write(f'  根页面 URL路径: {site.root_page.url_path}')
            self.stdout.write(f'  根页面 Path: {site.root_page.path}')
            self.stdout.write(f'  根页面 Depth: {site.root_page.depth}')
            
            # 检查页面是否在根页面下
            if page.path.startswith(site.root_page.path):
                self.stdout.write(self.style.SUCCESS('  [OK] 页面在此站点下'))
                # 检查相对路径
                relative_path = page.path[len(site.root_page.path):]
                self.stdout.write(f'  相对路径: {relative_path}')
            else:
                self.stdout.write(self.style.ERROR('  ✗ 页面不在此站点下'))
                self.stdout.write(f'    页面路径: {page.path}')
                self.stdout.write(f'    根页面路径: {site.root_page.path}')
        
        # 4. 检查 JobIndexPage
        self.stdout.write(f'\nJobIndexPage 检查:')
        job_index = JobIndexPage.objects.filter(slug='zhilian-jobs').first()
        if job_index:
            self.stdout.write(f'  ✓ 找到 JobIndexPage: {job_index.title} (ID: {job_index.id})')
            self.stdout.write(f'    URL路径: {job_index.url_path}')
            self.stdout.write(f'    Path: {job_index.path}')
            self.stdout.write(f'    Depth: {job_index.depth}')
            self.stdout.write(f'    父页面: {job_index.get_parent().title if job_index.get_parent() else "无"}')
            
            # 检查页面是否在 JobIndexPage 下
            if page.path.startswith(job_index.path):
                self.stdout.write(self.style.SUCCESS('  [OK] 页面在 JobIndexPage 下'))
            else:
                self.stdout.write(self.style.ERROR('  [ERROR] 页面不在 JobIndexPage 下'))
        else:
            self.stdout.write(self.style.ERROR('  [ERROR] 未找到 JobIndexPage'))
        
        # 5. 尝试模拟 Wagtail serve 的查找逻辑
        self.stdout.write(f'\n模拟 Wagtail serve 查找:')
        # Wagtail serve 会：
        # 1. 根据 hostname 找到 Site
        # 2. 从 Site.root_page 开始查找
        # 3. 根据 url_path 查找页面
        
        default_site = Site.objects.filter(is_default_site=True).first()
        if default_site:
            self.stdout.write(f'\n使用默认站点: {default_site.hostname}')
            root = default_site.root_page
            
            # 尝试从根页面查找
            # Wagtail 会移除 root_page 的 url_path，然后查找剩余部分
            root_url_path = root.url_path
            if url_path.startswith(root_url_path):
                relative_path = url_path[len(root_url_path):].lstrip('/')
                self.stdout.write(f'  根页面 URL路径: {root_url_path}')
                self.stdout.write(f'  相对路径: {relative_path}')
                
                # 尝试查找
                try:
                    found = Page.objects.filter(url_path=url_path).first()
                    if found:
                        self.stdout.write(self.style.SUCCESS(f'  [OK] 找到页面: {found.title}'))
                    else:
                        self.stdout.write(self.style.ERROR('  [ERROR] 未找到页面'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] 查找出错: {str(e)}'))
