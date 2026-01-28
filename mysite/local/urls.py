from django.conf import settings
from django.urls import include, path
from django.contrib import admin

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views
from jobs import views as jobs_views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    # 重要：accounts 路由必须在 Wagtail 路由之前
    # 使用 path 而不是 re_path，确保完全匹配 accounts/ 开头的所有路径
    path("accounts/", include("allauth.urls")),
    # 用户工作台和个人档案
    path("accounts/dashboard/", jobs_views.dashboard, name="dashboard"),
    path("accounts/profile/", jobs_views.edit_profile, name="account_profile"),
]

# 在 DEBUG 模式下添加静态文件服务
if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Wagtail 路由必须在最后，作为 catch-all
urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
]
