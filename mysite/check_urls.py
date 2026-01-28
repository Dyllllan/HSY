"""
临时诊断脚本：检查 URL 路由和 Wagtail 页面
运行方式：python manage.py shell < check_urls.py
"""
from django.urls import get_resolver
from wagtail.models import Page

print("=" * 50)
print("检查 URL 路由配置")
print("=" * 50)

resolver = get_resolver()
url_patterns = resolver.url_patterns

print("\nURL 模式列表（按顺序）：")
for i, pattern in enumerate(url_patterns, 1):
    print(f"{i}. {pattern.pattern} -> {pattern}")
    if hasattr(pattern, 'url_patterns'):
        for sub_pattern in pattern.url_patterns:
            print(f"   - {sub_pattern.pattern}")

print("\n" + "=" * 50)
print("检查 Wagtail 页面")
print("=" * 50)

# 检查是否有 slug 为 "accounts" 的页面
accounts_pages = Page.objects.filter(slug="accounts").live()
if accounts_pages.exists():
    print("\n⚠️  警告：发现 slug 为 'accounts' 的 Wagtail 页面！")
    for page in accounts_pages:
        print(f"  - 页面 ID: {page.id}, 标题: {page.title}, URL: {page.url}")
    print("\n这会导致 URL 冲突！请删除或重命名这些页面。")
else:
    print("\n✓ 没有发现 slug 为 'accounts' 的 Wagtail 页面")

# 检查所有根级页面
root = Page.get_first_root_node()
print(f"\n根页面下的直接子页面：")
for child in root.get_children().live():
    print(f"  - slug: '{child.slug}', 标题: {child.title}")

print("\n" + "=" * 50)
