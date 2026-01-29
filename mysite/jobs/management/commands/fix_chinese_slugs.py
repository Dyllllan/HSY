"""
修复 JobPage 中包含中文字符的 slug
使用方法: python manage.py fix_chinese_slugs
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from jobs.models import JobPage
import re


class Command(BaseCommand):
    help = '修复 JobPage 中包含中文字符的 slug'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要修复的数据，不实际修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 查找所有包含非ASCII字符的 slug
        all_jobs = JobPage.objects.live().specific()
        jobs_with_chinese_slug = []
        
        for job in all_jobs:
            if job.slug and re.search(r'[^\x00-\x7F]', job.slug):
                jobs_with_chinese_slug.append(job)
        
        count = len(jobs_with_chinese_slug)
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('[OK] 没有找到包含中文的 slug'))
            return
        
        self.stdout.write(f'找到 {count} 个包含中文的 slug')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('这是预览模式，不会实际修改数据'))
        
        fixed_count = 0
        skipped_count = 0
        
        for job in jobs_with_chinese_slug:
            # 生成新的 slug
            company = job.company_name or "未知公司"
            title = job.job_title or "未知职位"
            
            # 尝试使用 unidecode 处理中文
            try:
                from unidecode import unidecode
                company = unidecode(company)
                title = unidecode(title)
            except ImportError:
                # 如果没有 unidecode，移除所有非ASCII字符
                company = re.sub(r'[^\x00-\x7F]+', '', company)
                title = re.sub(r'[^\x00-\x7F]+', '', title)
            
            base_slug = slugify(f"{company}-{title}")
            
            # 如果 slug 为空，使用职位ID
            if not base_slug or len(base_slug.strip()) == 0:
                base_slug = f"job-{job.id}"
            
            # 确保 slug 只包含 ASCII 字符
            base_slug = re.sub(r'[^\w\-]', '', base_slug)
            base_slug = re.sub(r'-+', '-', base_slug).strip('-')
            
            # 如果 slug 太长，截断
            if len(base_slug) > 200:
                base_slug = base_slug[:200]
            
            # 确保 slug 唯一性
            slug = base_slug
            counter = 1
            while JobPage.objects.filter(slug=slug).exclude(pk=job.pk).exists():
                suffix = f"-{counter}"
                max_len = 200 - len(suffix)
                slug = base_slug[:max_len] + suffix
                counter += 1
            
            if not dry_run:
                try:
                    old_slug = job.slug
                    job.slug = slug
                    job.save(update_fields=['slug'])
                    # 如果页面已发布，需要重新发布以更新 URL
                    if job.live:
                        job.save_revision().publish()
                    fixed_count += 1
                    self.stdout.write(f'[OK] 修复: {job.title}')
                    self.stdout.write(f'      旧slug: {old_slug}')
                    self.stdout.write(f'      新slug: {slug}')
                except Exception as e:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'[ERROR] 跳过: {job.title} - 错误: {str(e)}')
                    )
            else:
                self.stdout.write(f'  将修复: {job.title}')
                self.stdout.write(f'    旧slug: {job.slug}')
                self.stdout.write(f'    新slug: {slug}')
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\n修复完成！成功修复 {fixed_count} 个，跳过 {skipped_count} 个'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'\n预览完成！将修复 {count} 个职位页面'
            ))
            self.stdout.write('运行时不加 --dry-run 参数来实际执行修复')
