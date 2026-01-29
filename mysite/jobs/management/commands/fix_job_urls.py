"""
修复 JobPage 的 URL 路径问题
使用方法: python manage.py fix_job_urls
"""
from django.core.management.base import BaseCommand
from jobs.models import JobPage, JobIndexPage
from wagtail.models import Page


class Command(BaseCommand):
    help = '修复 JobPage 的 URL 路径问题'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要修复的数据，不实际修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 获取所有已发布的 JobPage
        all_jobs = JobPage.objects.live().specific()
        count = all_jobs.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('[OK] 没有找到需要修复的页面'))
            return
        
        self.stdout.write(f'找到 {count} 个职位页面')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('这是预览模式，不会实际修改数据'))
        
        fixed_count = 0
        skipped_count = 0
        
        for job in all_jobs:
            if dry_run:
                parent = job.get_parent()
                parent_info = parent.title if parent else "无父页面"
                self.stdout.write(f'\n页面: {job.title} (ID: {job.id})')
                self.stdout.write(f'  当前URL路径: {job.url_path}')
                self.stdout.write(f'  父页面: {parent_info}')
                self.stdout.write(f'  Slug: {job.slug}')
            else:
                try:
                    # 检查父页面
                    parent = job.get_parent()
                    if not parent:
                        # 如果没有父页面，设置到 JobIndexPage
                        parent_page = JobIndexPage.objects.filter(slug='zhilian-jobs').first()
                        if not parent_page:
                            root_page = Page.objects.filter(depth=1).first()
                            if root_page:
                                parent_page = JobIndexPage(
                                    title='智联招聘职位',
                                    slug='zhilian-jobs',
                                    intro='来自智联招聘的职位信息'
                                )
                                root_page.add_child(instance=parent_page)
                                parent_page.save_revision().publish()
                        
                        if parent_page:
                            parent_page.add_child(instance=job)
                    
                    # 重新保存并发布以刷新 URL 路径
                    # Wagtail 的 url_path 是自动计算的，需要确保页面在正确的父页面下
                    parent = job.get_parent()
                    if parent:
                        # 直接保存页面，Wagtail 会自动更新 url_path
                        job.save(update_fields=[])
                        # 重新发布以更新 URL
                        if job.live:
                            revision = job.save_revision()
                            revision.publish()
                        # 刷新对象以获取最新的 url_path
                        job.refresh_from_db()
                        
                        # 验证 URL 路径是否正确
                        expected_url_path = f"{parent.url_path.rstrip('/')}/{job.slug}/"
                        if job.url_path != expected_url_path:
                            # 如果 URL 路径不正确，手动更新
                            from wagtail.models import Page
                            Page.objects.filter(pk=job.pk).update(
                                url_path=expected_url_path
                            )
                            job.refresh_from_db()
                    
                    fixed_count += 1
                    if fixed_count % 10 == 0:
                        self.stdout.write(f'已处理 {fixed_count}/{count} 个页面...')
                
                except Exception as e:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'[ERROR] 跳过: {job.title} (ID: {job.id}) - 错误: {str(e)}')
                    )
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\n修复完成！成功修复 {fixed_count} 个，跳过 {skipped_count} 个'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'\n预览完成！将修复 {count} 个页面'
            ))
            self.stdout.write('运行时不加 --dry-run 参数来实际执行修复')
