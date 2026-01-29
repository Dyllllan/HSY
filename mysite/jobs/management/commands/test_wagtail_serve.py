"""
测试 Wagtail serve 视图是否能找到页面
使用方法: python manage.py test_wagtail_serve --url-path /zhilian-jobs/java-44/
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from django.test import RequestFactory
from wagtail.views import serve


class Command(BaseCommand):
    help = '测试 Wagtail serve 视图'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url-path',
            type=str,
            default='/zhilian-jobs/java-44/',
            help='要测试的 URL 路径',
        )

    def handle(self, *args, **options):
        url_path = options['url_path']
        
        self.stdout.write(f'\n测试 URL 路径: {url_path}')
        
        # 查找页面
        page = Page.objects.filter(url_path=url_path).first()
        if page:
            self.stdout.write(f'✓ 找到页面: {page.title} (ID: {page.id})')
            self.stdout.write(f'  类型: {type(page.specific).__name__}')
            self.stdout.write(f'  已发布: {page.live}')
            self.stdout.write(f'  Path: {page.path}')
            self.stdout.write(f'  URL路径: {page.url_path}')
        else:
            self.stdout.write(self.style.ERROR('✗ 未找到页面'))
            # 尝试查找相似的路径
            similar = Page.objects.filter(url_path__icontains='java-44').first()
            if similar:
                self.stdout.write(f'  找到相似的路径: {similar.url_path}')
            return
        
        # 检查 Site 配置
        sites = Site.objects.all()
        self.stdout.write(f'\n站点配置:')
        for site in sites:
            self.stdout.write(f'  {site.hostname}:{site.port or 80} -> {site.root_page.title}')
            self.stdout.write(f'    根页面 URL路径: {site.root_page.url_path}')
            self.stdout.write(f'    是否默认: {site.is_default_site}')
            
            # 检查页面是否在根页面下
            if page.is_descendant_of(site.root_page):
                self.stdout.write(f'    ✓ 页面在此站点下')
            else:
                self.stdout.write(f'    ✗ 页面不在此站点下')
        
        # 尝试模拟请求
        self.stdout.write(f'\n模拟请求测试:')
        factory = RequestFactory()
        
        for site in sites:
            # 创建请求
            request = factory.get(url_path)
            request.META['HTTP_HOST'] = f"{site.hostname}:{site.port or 8000}"
            
            try:
                # 尝试查找页面
                found_site = Site.find_for_request(request)
                if found_site:
                    self.stdout.write(f'  匹配的站点: {found_site.hostname}')
                    # 尝试获取页面
                    try:
                        response = serve(request, url_path)
                        self.stdout.write(f'  ✓ Serve 视图返回: {response.status_code}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  ✗ Serve 视图出错: {str(e)}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  处理请求时出错: {str(e)}'))
