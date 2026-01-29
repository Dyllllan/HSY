"""
检查特定 JobPage 的 URL 路径
使用方法: python manage.py check_job_url --slug java-44
"""
from django.core.management.base import BaseCommand
from jobs.models import JobPage, JobIndexPage
from wagtail.models import Page


class Command(BaseCommand):
    help = '检查 JobPage 的 URL 路径'

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            help='要检查的职位 slug',
        )

    def handle(self, *args, **options):
        slug = options.get('slug')
        
        if slug:
            # 检查特定 slug
            jobs = JobPage.objects.filter(slug=slug).specific()
        else:
            # 检查所有职位
            jobs = JobPage.objects.live().specific()[:10]
        
        if not jobs.exists():
            self.stdout.write(self.style.WARNING(f'没有找到 slug 为 "{slug}" 的职位'))
            return
        
        for job in jobs:
            self.stdout.write(f'\n{"="*80}')
            self.stdout.write(f'职位: {job.title}')
            self.stdout.write(f'  ID: {job.id}')
            self.stdout.write(f'  Slug: {job.slug}')
            self.stdout.write(f'  URL路径: {job.url_path}')
            self.stdout.write(f'  URL: {job.url}')
            
            # 检查父页面
            parent = job.get_parent()
            if parent:
                self.stdout.write(f'  父页面: {parent.title} (ID: {parent.id})')
                self.stdout.write(f'  父页面类型: {type(parent.specific).__name__}')
                self.stdout.write(f'  父页面 slug: {parent.slug}')
                self.stdout.write(f'  父页面 URL路径: {parent.url_path}')
            else:
                self.stdout.write(self.style.ERROR('  父页面: 无'))
            
            # 检查页面状态
            self.stdout.write(f'  已发布: {job.live}')
            self.stdout.write(f'  深度: {job.depth}')
            self.stdout.write(f'  路径: {job.path}')
            
            # 检查是否能通过 URL 找到
            try:
                # 尝试多种方式查找
                found_page = Page.objects.filter(url_path=job.url_path).first()
                if found_page:
                    self.stdout.write(f'  通过URL路径找到: 是 (ID: {found_page.id})')
                else:
                    self.stdout.write(self.style.ERROR('  通过URL路径找到: 否'))
                
                # 尝试通过 path 查找
                found_by_path = Page.objects.filter(path=job.path).first()
                if found_by_path:
                    self.stdout.write(f'  通过path找到: 是 (ID: {found_by_path.id}, URL路径: {found_by_path.url_path})')
                
                # 检查父页面的 URL 路径
                if parent:
                    parent_url_path = parent.url_path
                    expected_child_path = f"{parent_url_path.rstrip('/')}/{job.slug}/"
                    self.stdout.write(f'  期望的完整URL路径: {expected_child_path}')
                    if expected_child_path != job.url_path:
                        self.stdout.write(self.style.WARNING(f'  ⚠️ URL路径不匹配！'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  检查URL路径时出错: {str(e)}'))
                import traceback
                self.stdout.write(traceback.format_exc())
