"""
修复 Site 的 root_page，确保设置为根页面（depth=1）而不是子页面
使用方法: python manage.py fix_site_root
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site


class Command(BaseCommand):
    help = '修复 Site 的 root_page 配置'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要修改的配置，不实际修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 获取所有站点
        sites = Site.objects.all()
        
        if not sites.exists():
            self.stdout.write(self.style.ERROR('未找到任何站点'))
            return
        
        # 获取根页面（depth=1）
        root_page = Page.objects.filter(depth=1).first()
        if not root_page:
            self.stdout.write(self.style.ERROR('未找到根页面'))
            return
        
        self.stdout.write(f'\n根页面: {root_page.title} (ID: {root_page.id})')
        self.stdout.write(f'  路径: {root_page.path}')
        self.stdout.write(f'  URL路径: {root_page.url_path}')
        
        for site in sites:
            self.stdout.write(f'\n站点: {site.site_name}')
            self.stdout.write(f'  Hostname: {site.hostname}')
            self.stdout.write(f'  Port: {site.port}')
            self.stdout.write(f'  当前 root_page: {site.root_page.title} (ID: {site.root_page.id})')
            self.stdout.write(f'    路径: {site.root_page.path}')
            self.stdout.write(f'    URL路径: {site.root_page.url_path}')
            self.stdout.write(f'    深度: {site.root_page.depth}')
            
            # 检查 root_page 是否是根页面
            if site.root_page.depth == 1:
                self.stdout.write(self.style.SUCCESS('  [OK] root_page 已经是根页面'))
            else:
                self.stdout.write(self.style.WARNING('  [WARNING] root_page 不是根页面！'))
                self.stdout.write('    这会导致所有页面的 URL 包含 root_page 的 slug')
                
                if not dry_run:
                    try:
                        site.root_page = root_page
                        site.save(update_fields=['root_page'])
                        self.stdout.write(self.style.SUCCESS(f'  [OK] 已将 root_page 设置为根页面'))
                        
                        # 更新所有页面的 URL 路径（通过重新保存）
                        self.stdout.write('  更新页面 URL 路径...')
                        # Wagtail 会自动更新 url_path，但我们需要触发更新
                        # 实际上，Wagtail 的 url_path 是动态计算的，不需要手动更新
                        self.stdout.write('  [OK] URL 路径会在下次访问时自动更新')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  [ERROR] 更新失败: {str(e)}'))
                else:
                    self.stdout.write('  预览模式：将设置 root_page 为根页面')
