"""
创建或检查 RecommendationsPage 页面实例
使用方法: python manage.py create_recommendations_page
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from jobs.models import RecommendationsPage


class Command(BaseCommand):
    help = '创建或检查 RecommendationsPage 页面实例'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要执行的操作，不实际创建',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 查找是否已存在 RecommendationsPage
        existing_page = RecommendationsPage.objects.filter(slug='recommendations').first()
        
        if existing_page:
            self.stdout.write(self.style.SUCCESS(f'\n[OK] RecommendationsPage 已存在'))
            self.stdout.write(f'  标题: {existing_page.title}')
            self.stdout.write(f'  Slug: {existing_page.slug}')
            self.stdout.write(f'  URL路径: {existing_page.url_path}')
            self.stdout.write(f'  父页面: {existing_page.get_parent().title if existing_page.get_parent() else "无"}')
            self.stdout.write(f'  是否发布: {"是" if existing_page.live else "否"}')
            self.stdout.write(f'  深度: {existing_page.depth}')
            
            if not existing_page.live:
                self.stdout.write(self.style.WARNING('  [WARNING] 页面未发布，需要发布后才能访问'))
                if not dry_run:
                    try:
                        existing_page.save_revision().publish()
                        self.stdout.write(self.style.SUCCESS('  [OK] 已发布页面'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  [ERROR] 发布失败: {str(e)}'))
        else:
            self.stdout.write(self.style.WARNING('\n[WARNING] RecommendationsPage 不存在，将创建'))
            
            if not dry_run:
                try:
                    # 获取 Site 的 root_page（通常是 HomePage 或根页面）
                    default_site = Site.objects.filter(is_default_site=True).first()
                    if default_site:
                        parent_page = default_site.root_page
                    else:
                        # 如果没有 Site，使用根页面
                        parent_page = Page.objects.filter(depth=1).first()
                    
                    if not parent_page:
                        self.stdout.write(self.style.ERROR('  [ERROR] 未找到父页面'))
                        return
                    
                    self.stdout.write(f'  父页面: {parent_page.title} (ID: {parent_page.id})')
                    
                    # 创建 RecommendationsPage
                    recommendations_page = RecommendationsPage(
                        title='个性化推荐',
                        slug='recommendations',
                        intro='根据您的个人档案和偏好，为您推荐合适的职位'
                    )
                    
                    parent_page.add_child(instance=recommendations_page)
                    recommendations_page.save_revision().publish()
                    
                    self.stdout.write(self.style.SUCCESS('  [OK] 已创建并发布 RecommendationsPage'))
                    self.stdout.write(f'  URL路径: {recommendations_page.url_path}')
                    self.stdout.write(f'  访问地址: http://127.0.0.1:8000/recommendations/')
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] 创建失败: {str(e)}'))
                    import traceback
                    self.stdout.write(traceback.format_exc())
            else:
                self.stdout.write('  预览模式：将创建 RecommendationsPage')
                self.stdout.write('    - 标题: 个性化推荐')
                self.stdout.write('    - Slug: recommendations')
                self.stdout.write('    - 父页面: Site.root_page')
