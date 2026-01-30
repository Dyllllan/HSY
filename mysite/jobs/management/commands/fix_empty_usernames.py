"""
管理命令：修复空字符串的 username 记录

使用方法：
    python manage.py fix_empty_usernames
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import time

User = get_user_model()


class Command(BaseCommand):
    help = '修复数据库中空字符串的 username 记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要修复的记录，不实际修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 查找所有 username 为空字符串或 None 的用户
        empty_username_users = User.objects.filter(username__in=['', None]) | User.objects.filter(username='')
        
        count = empty_username_users.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ 没有发现空 username 的记录')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'发现 {count} 个空 username 的记录')
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('这是预览模式，不会实际修改数据'))
        
        fixed_count = 0
        deleted_count = 0
        
        for user in empty_username_users:
            if user.email:
                # 如果用户有邮箱，使用邮箱生成唯一的 username
                base_username = user.email.split('@')[0]
                username = base_username
                counter = 1
                
                # 确保 username 唯一
                while User.objects.filter(username=username).exclude(pk=user.pk).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                    if counter > 1000:
                        username = f"{base_username}_{int(time.time())}"
                        break
                
                if not dry_run:
                    user.username = username
                    user.save()
                    self.stdout.write(
                        f'  ✓ 用户 {user.email}: username 设置为 "{username}"'
                    )
                else:
                    self.stdout.write(
                        f'  [预览] 用户 {user.email}: 将设置 username 为 "{username}"'
                    )
                fixed_count += 1
            else:
                # 如果用户没有邮箱，删除该用户（可能是无效数据）
                if not dry_run:
                    self.stdout.write(
                        self.style.WARNING(f'  ✗ 删除无效用户 ID={user.pk} (无邮箱)')
                    )
                    user.delete()
                    deleted_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  [预览] 将删除无效用户 ID={user.pk} (无邮箱)')
                    )
                    deleted_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n预览完成：将修复 {fixed_count} 个记录，删除 {deleted_count} 个无效记录'
                )
            )
            self.stdout.write('运行时不加 --dry-run 参数来实际执行修复')
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ 修复完成：已修复 {fixed_count} 个记录，删除 {deleted_count} 个无效记录'
                )
            )
