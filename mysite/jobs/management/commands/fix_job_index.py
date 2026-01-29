"""
修复 JobIndexPage 的位置，确保 slug='jobs' 的页面在 Site.root_page 下
使用方法: python manage.py fix_job_index
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from jobs.models import JobIndexPage


class Command(BaseCommand):
    help = '修复 JobIndexPage 的位置'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要执行的操作，不实际修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 获取 Site 的 root_page
        default_site = Site.objects.filter(is_default_site=True).first()
        if not default_site:
            self.stdout.write(self.style.ERROR('\n[ERROR] 未找到默认站点'))
            return
        
        root_page = default_site.root_page
        self.stdout.write(f'\nSite root_page: {root_page.title} (ID: {root_page.id})')
        self.stdout.write(f'  URL路径: {root_page.url_path}')
        
        # 查找 slug='jobs' 的 JobIndexPage
        jobs_page = JobIndexPage.objects.filter(slug='jobs').first()
        
        if not jobs_page:
            self.stdout.write(self.style.WARNING('\n[WARNING] 未找到 slug="jobs" 的 JobIndexPage'))
            self.stdout.write('将创建一个新的 JobIndexPage')
            
            if not dry_run:
                try:
                    jobs_page = JobIndexPage(
                        title='职位列表',
                        slug='jobs',
                        intro='浏览所有职位信息'
                    )
                    root_page.add_child(instance=jobs_page)
                    jobs_page.save_revision().publish()
                    self.stdout.write(self.style.SUCCESS('\n[OK] 已创建 JobIndexPage (slug="jobs")'))
                    self.stdout.write(f'  URL路径: {jobs_page.url_path}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'\n[ERROR] 创建失败: {str(e)}'))
                    import traceback
                    self.stdout.write(traceback.format_exc())
                    return
            else:
                self.stdout.write('\n预览模式：将创建 JobIndexPage (slug="jobs")')
                return
        else:
            self.stdout.write(f'\n找到 JobIndexPage (slug="jobs"):')
            self.stdout.write(f'  ID: {jobs_page.id}')
            self.stdout.write(f'  标题: {jobs_page.title}')
            self.stdout.write(f'  URL路径: {jobs_page.url_path}')
            self.stdout.write(f'  深度: {jobs_page.depth}')
            
            current_parent = jobs_page.get_parent()
            if current_parent:
                self.stdout.write(f'  当前父页面: {current_parent.title} (ID: {current_parent.id})')
                self.stdout.write(f'    路径: {current_parent.path}')
                self.stdout.write(f'    URL路径: {current_parent.url_path}')
                self.stdout.write(f'    深度: {current_parent.depth}')
            
            # 检查是否需要移动
            if current_parent and current_parent.id == root_page.id:
                self.stdout.write(self.style.SUCCESS('\n[OK] JobIndexPage 已在正确的父页面下'))
            else:
                self.stdout.write(self.style.WARNING('\n[WARNING] JobIndexPage 不在 Site.root_page 下'))
                self.stdout.write('需要移动到根页面下')
                
                if not dry_run:
                    try:
                        # 移动页面到根页面下
                        jobs_page.move(root_page, pos='last-child')
                        # 刷新对象以获取新的 URL 路径
                        jobs_page.refresh_from_db()
                        
                        self.stdout.write(self.style.SUCCESS('\n[OK] 已移动 JobIndexPage 到根页面下'))
                        self.stdout.write(f'  新 URL路径: {jobs_page.url_path}')
                        
                        # 确保页面已发布
                        if not jobs_page.live:
                            jobs_page.save_revision().publish()
                            self.stdout.write(self.style.SUCCESS('  [OK] 已发布页面'))
                        
                        # 更新所有子页面的 URL 路径（如果有）
                        descendants = jobs_page.get_descendants()
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
                    self.stdout.write('\n预览模式：将移动 JobIndexPage 到根页面下')
        
        # 检查页面是否已发布
        jobs_page.refresh_from_db()
        if not jobs_page.live:
            self.stdout.write(self.style.WARNING('\n[WARNING] 页面未发布'))
            if not dry_run:
                try:
                    jobs_page.save_revision().publish()
                    self.stdout.write(self.style.SUCCESS('  [OK] 已发布页面'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] 发布失败: {str(e)}'))
        
        # 显示最终状态
        jobs_page.refresh_from_db()
        self.stdout.write(f'\n最终状态:')
        self.stdout.write(f'  URL路径: {jobs_page.url_path}')
        self.stdout.write(f'  访问地址: http://127.0.0.1:8000/jobs/')
        
        # 检查其他 JobIndexPage
        other_pages = JobIndexPage.objects.exclude(slug='jobs')
        if other_pages.exists():
            self.stdout.write(f'\n其他 JobIndexPage ({other_pages.count()} 个):')
            for page in other_pages:
                self.stdout.write(f'  - {page.title} (slug: {page.slug}, URL: {page.url_path})')
                self.stdout.write(f'    子页面数量: {page.get_children().count()}')
