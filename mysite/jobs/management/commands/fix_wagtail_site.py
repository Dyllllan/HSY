"""
修复 Wagtail Site 配置，确保能匹配 127.0.0.1 和 localhost
使用方法: python manage.py fix_wagtail_site
"""
from django.core.management.base import BaseCommand
from wagtail.models import Site, Page


class Command(BaseCommand):
    help = '修复 Wagtail Site 配置'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要修改的配置，不实际修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 获取默认站点
        default_site = Site.objects.filter(is_default_site=True).first()
        
        if not default_site:
            # 如果没有默认站点，创建一个
            root_page = Page.objects.filter(depth=1).first()
            if root_page:
                if not dry_run:
                    default_site = Site.objects.create(
                        hostname='localhost',
                        port=8000,
                        root_page=root_page,
                        is_default_site=True,
                        site_name='Local Development'
                    )
                    self.stdout.write(self.style.SUCCESS('创建了新的默认站点'))
                else:
                    self.stdout.write('将创建新的默认站点')
            else:
                self.stdout.write(self.style.ERROR('找不到根页面，无法创建站点'))
                return
        else:
            self.stdout.write(f'\n当前默认站点配置:')
            self.stdout.write(f'  Hostname: {default_site.hostname}')
            self.stdout.write(f'  Port: {default_site.port}')
            self.stdout.write(f'  根页面: {default_site.root_page.title}')
        
        # 检查是否需要添加 127.0.0.1 的站点配置
        if default_site.hostname == 'localhost':
            # 检查是否已经有 127.0.0.1 的站点
            site_127 = Site.objects.filter(hostname='127.0.0.1').first()
            
            if not site_127:
                if not dry_run:
                    # 创建一个 127.0.0.1 的站点，指向同一个根页面
                    Site.objects.create(
                        hostname='127.0.0.1',
                        port=8000,
                        root_page=default_site.root_page,
                        is_default_site=False,
                        site_name='Local Development (127.0.0.1)'
                    )
                    self.stdout.write(self.style.SUCCESS('创建了 127.0.0.1 的站点配置'))
                else:
                    self.stdout.write('将创建 127.0.0.1 的站点配置')
            else:
                self.stdout.write('127.0.0.1 的站点配置已存在')
        
        # 更新默认站点，使其也能匹配 127.0.0.1（通过设置 hostname 为 *）
        # 或者确保 localhost 和 127.0.0.1 都能工作
        if not dry_run and default_site.hostname == 'localhost':
            # Wagtail 支持通配符 hostname
            # 但更好的方式是确保两个 hostname 都有配置
            self.stdout.write(self.style.SUCCESS('\n站点配置已更新'))
        
        # 测试一个页面
        from jobs.models import JobPage
        test_job = JobPage.objects.filter(slug='java-44').first()
        if test_job:
            self.stdout.write(f'\n测试页面: {test_job.title}')
            self.stdout.write(f'  URL路径: {test_job.url_path}')
            try:
                # 尝试获取 URL
                site = Site.find_for_request(None)
                if site:
                    self.stdout.write(f'  匹配的站点: {site.hostname}')
                    self.stdout.write(f'  完整URL: http://{site.hostname}:{site.port or 8000}{test_job.url_path}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  获取URL时出错: {str(e)}'))
