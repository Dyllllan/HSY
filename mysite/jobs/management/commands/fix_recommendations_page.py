"""
修复 RecommendationsPage 的位置，确保它在 Site.root_page 下
使用方法: python manage.py fix_recommendations_page
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from jobs.models import RecommendationsPage


class Command(BaseCommand):
    help = '修复 RecommendationsPage 的位置'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要执行的操作，不实际修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 查找 RecommendationsPage
        recommendations_page = RecommendationsPage.objects.filter(slug='recommendations').first()
        
        if not recommendations_page:
            self.stdout.write(self.style.ERROR('\n[ERROR] RecommendationsPage 不存在'))
            self.stdout.write('请先运行: python manage.py create_recommendations_page')
            return
        
        self.stdout.write(f'\n当前 RecommendationsPage 状态:')
        self.stdout.write(f'  标题: {recommendations_page.title}')
        self.stdout.write(f'  Slug: {recommendations_page.slug}')
        self.stdout.write(f'  URL路径: {recommendations_page.url_path}')
        self.stdout.write(f'  深度: {recommendations_page.depth}')
        
        current_parent = recommendations_page.get_parent()
        if current_parent:
            self.stdout.write(f'  当前父页面: {current_parent.title} (ID: {current_parent.id})')
            self.stdout.write(f'    路径: {current_parent.path}')
            self.stdout.write(f'    URL路径: {current_parent.url_path}')
            self.stdout.write(f'    深度: {current_parent.depth}')
        
        # 获取 Site 的 root_page
        default_site = Site.objects.filter(is_default_site=True).first()
        if not default_site:
            self.stdout.write(self.style.ERROR('\n[ERROR] 未找到默认站点'))
            return
        
        root_page = default_site.root_page
        self.stdout.write(f'\nSite root_page: {root_page.title} (ID: {root_page.id})')
        self.stdout.write(f'  路径: {root_page.path}')
        self.stdout.write(f'  URL路径: {root_page.url_path}')
        self.stdout.write(f'  深度: {root_page.depth}')
        
        # 检查是否需要移动
        if current_parent and current_parent.id == root_page.id:
            self.stdout.write(self.style.SUCCESS('\n[OK] RecommendationsPage 已在正确的父页面下'))
        else:
            self.stdout.write(self.style.WARNING('\n[WARNING] RecommendationsPage 不在 Site.root_page 下'))
            self.stdout.write('需要移动到根页面下')
            
            if not dry_run:
                try:
                    # 移动页面到根页面下
                    recommendations_page.move(root_page, pos='last-child')
                    # 刷新对象以获取新的 URL 路径
                    recommendations_page.refresh_from_db()
                    
                    self.stdout.write(self.style.SUCCESS('\n[OK] 已移动 RecommendationsPage 到根页面下'))
                    self.stdout.write(f'  新 URL路径: {recommendations_page.url_path}')
                    
                    # 确保页面已发布
                    if not recommendations_page.live:
                        recommendations_page.save_revision().publish()
                        self.stdout.write(self.style.SUCCESS('  [OK] 已发布页面'))
                    
                    # 更新所有子页面的 URL 路径（如果有）
                    descendants = recommendations_page.get_descendants()
                    if descendants.exists():
                        self.stdout.write(f'  更新 {descendants.count()} 个子页面的 URL 路径...')
                        for desc in descendants:
                            desc.save()
                        self.stdout.write(self.style.SUCCESS('  [OK] 子页面 URL 路径已更新'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'\n[ERROR] 移动失败: {str(e)}'))
                    import traceback
                    self.stdout.write(traceback.format_exc())
            else:
                self.stdout.write('\n预览模式：将移动 RecommendationsPage 到根页面下')
        
        # 检查页面是否已发布
        if not recommendations_page.live:
            self.stdout.write(self.style.WARNING('\n[WARNING] 页面未发布'))
            if not dry_run:
                try:
                    recommendations_page.save_revision().publish()
                    self.stdout.write(self.style.SUCCESS('  [OK] 已发布页面'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] 发布失败: {str(e)}'))
        
        # 显示最终状态
        recommendations_page.refresh_from_db()
        self.stdout.write(f'\n最终状态:')
        self.stdout.write(f'  URL路径: {recommendations_page.url_path}')
        self.stdout.write(f'  访问地址: http://127.0.0.1:8000/recommendations/')
