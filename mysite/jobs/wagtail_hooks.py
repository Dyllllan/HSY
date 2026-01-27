from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, TabbedInterface, ObjectList
from .models import StudentProfile, JobPage
from wagtail.admin.ui.tables import DateColumn
from wagtail.admin.views.generic.models import IndexView
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from django.urls import reverse, path
from django.db.models import Count

@hooks.register('register_admin_menu_item')
def register_job_stats_menu_item():
    return MenuItem(
        label='职位统计',
        url=reverse('job_stats'),
        icon_name='chart-bar',
        order=1000
    )

class JobStatsView(IndexView):
    model = JobPage
    template_name = 'jobs/admin/job_stats.html'
    page_title = '职位数据统计'
    
    def get_queryset(self):
        # 按来源网站分组统计
        return super().get_queryset()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 添加统计数据
        context['stats'] = {
            'total_jobs': JobPage.objects.count(),
            'by_source': JobPage.objects.values('source_website').annotate(count=Count('id')),
            'by_type': JobPage.objects.values('job_type').annotate(count=Count('id')),
        }
        return context

@hooks.register('register_admin_urls')
def register_job_stats_url():
    return [
        path('job-stats/', JobStatsView.as_view(), name='job_stats'),
    ]

# 在职位列表中添加自定义列和批量操作
@hooks.register('construct_explorer_page_queryset')
def filter_jobs_by_source(parent_page, pages, request):
    # 允许按来源筛选
    source = request.GET.get('source')
    if source:
        pages = pages.filter(source_website=source)
    return pages

class StudentProfileViewSet(SnippetViewSet):
    """在Wagtail后台管理学生档案"""
    model = StudentProfile
    menu_label = '学生档案'
    menu_icon = 'user'
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False
    
    list_display = ['user', 'school', 'major', 'graduation_year', 'is_verified']
    list_filter = ['school', 'major', 'graduation_year', 'is_verified']
    search_fields = ['user__username', 'user__email', 'student_id', 'resume_text']
    
    # 自定义编辑界面面板
    edit_handler = TabbedInterface([
        ObjectList([
            FieldPanel('user', read_only=True),
            MultiFieldPanel([
                FieldPanel('student_id'),
                FieldPanel('school'),
                FieldPanel('major'),
                FieldPanel('graduation_year'),
            ], heading='基本信息'),
        ], heading='身份信息'),
        
        ObjectList([
            MultiFieldPanel([
                FieldPanel('preferred_job_types'),
                FieldPanel('preferred_locations'),
            ], heading='求职偏好'),
        ], heading='求职设置'),
        
        ObjectList([
            FieldPanel('resume'),
            FieldPanel('resume_text'),
        ], heading='简历资料'),
        
        ObjectList([
            FieldPanel('is_verified'),
            FieldPanel('last_active', read_only=True),
            FieldPanel('created_at', read_only=True),
        ], heading='状态信息'),
    ])
    
    def get_queryset(self, request):
        """只显示非管理员的学生档案"""
        qs = super().get_queryset(request)
        # 过滤掉超级用户和员工用户
        return qs.filter(user__is_superuser=False, user__is_staff=False)

# 注册到Wagtail后台
register_snippet(StudentProfileViewSet)