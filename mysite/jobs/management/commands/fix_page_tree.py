"""
修复页面树结构，确保 JobIndexPage 在 Site.root_page 下
使用方法: python manage.py fix_page_tree
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from jobs.models import JobPage, JobIndexPage
from home.models import HomePage


class Command(BaseCommand):
    help = '修复页面树结构'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要修改的结构，不实际修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 获取默认站点
        default_site = Site.objects.filter(is_default_site=True).first()
        if not default_site:
            self.stdout.write(self.style.ERROR('未找到默认站点'))
            return
        
        root_page = default_site.root_page
        self.stdout.write(f'\n默认站点根页面: {root_page.title} (ID: {root_page.id})')
        self.stdout.write(f'  路径: {root_page.path}')
        self.stdout.write(f'  URL路径: {root_page.url_path}')
        
        # 检查 JobIndexPage
        job_index = JobIndexPage.objects.filter(slug='zhilian-jobs').first()
        if not job_index:
            self.stdout.write(self.style.ERROR('未找到 JobIndexPage'))
            return
        
        self.stdout.write(f'\nJobIndexPage: {job_index.title} (ID: {job_index.id})')
        self.stdout.write(f'  当前路径: {job_index.path}')
        self.stdout.write(f'  当前URL路径: {job_index.url_path}')
        
        current_parent = job_index.get_parent()
        if current_parent:
            self.stdout.write(f'  当前父页面: {current_parent.title} (ID: {current_parent.id})')
            self.stdout.write(f'    父页面路径: {current_parent.path}')
            self.stdout.write(f'    父页面URL路径: {current_parent.url_path}')
        
        # 检查 JobIndexPage 是否在 root_page 下
        if job_index.path.startswith(root_page.path):
            self.stdout.write(self.style.SUCCESS('\n[OK] JobIndexPage 在根页面下'))
        else:
            self.stdout.write(self.style.ERROR('\n[ERROR] JobIndexPage 不在根页面下！'))
            self.stdout.write('需要将 JobIndexPage 移动到根页面下')
            
            if not dry_run:
                try:
                    # 如果当前有父页面，需要先移除
                    if current_parent and current_parent.id != root_page.id:
                        # 获取所有子页面
                        children = list(job_index.get_children())
                        # 移动到新父页面
                        job_index.move(root_page, pos='last-child')
                        # 重新添加子页面
                        for child in children:
                            child.move(job_index, pos='last-child')
                    else:
                        # 直接移动到根页面下
                        job_index.move(root_page, pos='last-child')
                    
                    # 重新发布
                    job_index.save_revision().publish()
                    job_index.refresh_from_db()
                    
                    self.stdout.write(self.style.SUCCESS(f'\n[OK] 已将 JobIndexPage 移动到根页面下'))
                    self.stdout.write(f'  新路径: {job_index.path}')
                    self.stdout.write(f'  新URL路径: {job_index.url_path}')
                    
                    # 更新所有子页面的 URL 路径
                    self.stdout.write('\n更新子页面的 URL 路径...')
                    job_pages = JobPage.objects.filter(path__startswith=job_index.path).live().specific()
                    count = job_pages.count()
                    self.stdout.write(f'找到 {count} 个子页面需要更新')
                    
                    updated = 0
                    for job in job_pages:
                        try:
                            job.save(update_fields=[])
                            if job.live:
                                job.save_revision().publish()
                            job.refresh_from_db()
                            updated += 1
                            if updated % 10 == 0:
                                self.stdout.write(f'已更新 {updated}/{count} 个页面...')
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'更新失败: {job.title} - {str(e)}'))
                    
                    self.stdout.write(self.style.SUCCESS(f'\n[OK] 已更新 {updated} 个子页面'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'移动失败: {str(e)}'))
                    import traceback
                    self.stdout.write(traceback.format_exc())
            else:
                self.stdout.write('\n预览模式：将移动 JobIndexPage 到根页面下')
