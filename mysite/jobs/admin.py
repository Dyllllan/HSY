from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.db.models import Count, Q
from django.urls import path
from django.shortcuts import render
from django.utils.safestring import mark_safe

from .models import StudentProfile, JobApplication, JobPage


# 内联显示学生档案
class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = '学生档案'
    fields = (
        'student_id', 'school', 'major', 'graduation_year',
        'preferred_job_types', 'preferred_locations',
        'is_verified', 'last_active', 'created_at'
    )
    readonly_fields = ('last_active', 'created_at')


# 自定义用户管理类
# 先取消默认注册（如果已注册），然后注册我们的自定义Admin
try:
    admin.site.unregister(User)
except NotRegistered:
    pass

class CustomUserAdmin(BaseUserAdmin):
    """自定义用户管理界面，显示用户基本信息和统计"""
    
    inlines = [StudentProfileInline]
    
    list_display = (
        'username', 'email', 'full_name', 'is_active', 'is_staff',
        'date_joined', 'user_stats'
    )
    
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 'date_joined',
        'groups'
    )
    
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('统计信息', {
            'fields': ('statistics_summary',),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('statistics_summary',)
    
    def user_stats(self, obj):
        """在列表页显示简要统计"""
        if not obj.pk:
            return "-"
        try:
            applications = JobApplication.objects.filter(user=obj)
            saved = applications.filter(status='saved').count()
            applied = applications.filter(status='applied').count()
            return format_html(
                '收藏: <span style="color: #007cba;">{}</span> | '
                '申请: <span style="color: #28a745;">{}</span>',
                saved, applied
            )
        except:
            return "-"
    user_stats.short_description = "活动统计"
    
    def full_name(self, obj):
        """显示用户全名"""
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return "-"
    full_name.short_description = "姓名"
    
    def statistics_summary(self, obj):
        """显示用户统计信息"""
        if not obj.pk:
            return "保存后显示统计信息"
        
        # 获取学生档案
        try:
            profile = obj.student_profile
            has_profile = True
        except StudentProfile.DoesNotExist:
            has_profile = False
        
        # 统计职位申请相关数据
        applications = JobApplication.objects.filter(user=obj)
        saved_count = applications.filter(status='saved').count()
        applied_count = applications.filter(status='applied').count()
        viewed_count = applications.filter(status='viewed').count()
        total_applications = applications.count()
        
        # 统计最近活动
        recent_applications = applications.order_by('-updated_at')[:5]
        
        html = f"""
        <div style="padding: 10px; background-color: #f9f9f9; border-radius: 5px;">
            <h3 style="margin-top: 0;">用户统计信息</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px; font-weight: bold;">学生档案：</td>
                    <td style="padding: 5px;">{'已创建' if has_profile else '未创建'}</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">收藏职位：</td>
                    <td style="padding: 5px;"><span style="color: #007cba;">{saved_count}</span> 个</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">申请职位：</td>
                    <td style="padding: 5px;"><span style="color: #28a745;">{applied_count}</span> 个</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">查看职位：</td>
                    <td style="padding: 5px;"><span style="color: #17a2b8;">{viewed_count}</span> 个</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">总操作数：</td>
                    <td style="padding: 5px;"><strong>{total_applications}</strong> 次</td>
                </tr>
            </table>
        """
        
        if has_profile:
            html += f"""
            <div style="margin-top: 15px;">
                <h4>学生档案信息</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">学校：</td>
                        <td style="padding: 5px;">{profile.get_school_display()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">专业：</td>
                        <td style="padding: 5px;">{profile.get_major_display()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">毕业年份：</td>
                        <td style="padding: 5px;">{profile.graduation_year}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">偏好地点：</td>
                        <td style="padding: 5px;">{profile.preferred_locations}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">最后活跃：</td>
                        <td style="padding: 5px;">{profile.last_active.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
            </div>
            """
        
        if recent_applications:
            html += """
            <div style="margin-top: 15px;">
                <h4>最近活动</h4>
                <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd;">
                    <thead>
                        <tr style="background-color: #f0f0f0;">
                            <th style="padding: 8px; text-align: left;">职位</th>
                            <th style="padding: 8px; text-align: left;">状态</th>
                            <th style="padding: 8px; text-align: left;">时间</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for app in recent_applications:
                status_colors = {
                    'saved': '#007cba',
                    'applied': '#28a745',
                    'viewed': '#17a2b8',
                    'contacted': '#ffc107',
                    'rejected': '#dc3545',
                    'accepted': '#28a745'
                }
                status_color = status_colors.get(app.status, '#6c757d')
                html += f"""
                        <tr>
                            <td style="padding: 5px;">{app.job_page.job_title}</td>
                            <td style="padding: 5px;"><span style="color: {status_color};">{app.get_status_display()}</span></td>
                            <td style="padding: 5px;">{app.updated_at.strftime('%Y-%m-%d %H:%M')}</td>
                        </tr>
                """
            html += """
                    </tbody>
                </table>
            </div>
            """
        
        html += "</div>"
        return mark_safe(html)
    
    statistics_summary.short_description = "统计信息"
    
    def get_urls(self):
        """添加统计页面URL"""
        urls = super().get_urls()
        custom_urls = [
            path('statistics/', self.admin_site.admin_view(statistics_view), name='user_statistics'),
        ]
        return custom_urls + urls

# 注册自定义用户管理类
admin.site.register(User, CustomUserAdmin)


# 学生档案管理
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """学生档案管理界面"""
    
    list_display = (
        'user_info', 'school', 'major', 'graduation_year',
        'is_verified', 'last_active', 'created_at', 'activity_summary'
    )
    
    list_filter = (
        'school', 'major', 'graduation_year', 'is_verified',
        'created_at'
    )
    
    search_fields = (
        'user__username', 'user__email', 'user__first_name',
        'user__last_name', 'student_id'
    )
    
    readonly_fields = ('created_at', 'last_active', 'activity_stats', 'activity_summary')
    
    fieldsets = (
        ('用户信息', {
            'fields': ('user', 'student_id')
        }),
        ('学生信息', {
            'fields': ('school', 'major', 'graduation_year')
        }),
        ('求职偏好', {
            'fields': ('preferred_job_types', 'preferred_locations')
        }),
        ('简历信息', {
            'fields': ('resume', 'resume_text'),
            'classes': ('collapse',)
        }),
        ('状态信息', {
            'fields': ('is_verified', 'last_active', 'created_at')
        }),
        ('活动统计', {
            'fields': ('activity_stats', 'activity_summary'),
            'classes': ('collapse',)
        }),
    )
    
    def user_info(self, obj):
        """显示用户信息"""
        user = obj.user
        email = user.email or "-"
        name = f"{user.first_name} {user.last_name}".strip() or user.username
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            name, email
        )
    user_info.short_description = "用户"
    
    def activity_summary(self, obj):
        """在列表页显示简要活动统计"""
        if not obj.pk:
            return "-"
        try:
            applications = JobApplication.objects.filter(user=obj.user)
            saved = applications.filter(status='saved').count()
            applied = applications.filter(status='applied').count()
            return format_html(
                '收藏: <span style="color: #007cba;">{}</span> | '
                '申请: <span style="color: #28a745;">{}</span>',
                saved, applied
            )
        except:
            return "-"
    activity_summary.short_description = "活动统计"
    
    def activity_stats(self, obj):
        """显示活动统计"""
        if not obj.pk:
            return "保存后显示统计信息"
        
        applications = JobApplication.objects.filter(user=obj.user)
        saved_count = applications.filter(status='saved').count()
        applied_count = applications.filter(status='applied').count()
        viewed_count = applications.filter(status='viewed').count()
        total_count = applications.count()
        
        html = f"""
        <div style="padding: 10px; background-color: #f9f9f9; border-radius: 5px;">
            <h4>职位活动统计</h4>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px; font-weight: bold;">收藏职位：</td>
                    <td style="padding: 5px;"><span style="color: #007cba;">{saved_count}</span> 个</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">申请职位：</td>
                    <td style="padding: 5px;"><span style="color: #28a745;">{applied_count}</span> 个</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">查看职位：</td>
                    <td style="padding: 5px;"><span style="color: #17a2b8;">{viewed_count}</span> 个</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">总操作数：</td>
                    <td style="padding: 5px;"><strong>{total_count}</strong> 次</td>
                </tr>
            </table>
        </div>
        """
        return mark_safe(html)
    
    activity_stats.short_description = "活动统计"


# 职位申请管理
@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    """职位申请管理界面"""
    
    list_display = (
        'user_info', 'job_info', 'status', 'applied_date',
        'created_at', 'updated_at'
    )
    
    list_filter = ('status', 'created_at', 'applied_date', 'source')
    
    search_fields = (
        'user__username', 'user__email',
        'job_page__job_title', 'job_page__company_name'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'job_page', 'status')
        }),
        ('详细信息', {
            'fields': ('applied_date', 'notes')
        }),
        ('追踪信息', {
            'fields': ('source', 'ip_address'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def user_info(self, obj):
        """显示用户信息"""
        user = obj.user
        email = user.email or "-"
        name = f"{user.first_name} {user.last_name}".strip() or user.username
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            name, email
        )
    user_info.short_description = "用户"
    
    def job_info(self, obj):
        """显示职位信息"""
        job = obj.job_page
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            job.job_title, job.company_name
        )
    job_info.short_description = "职位"


# 统计视图函数
def statistics_view(request):
    """显示用户统计信息页面"""
    # 总用户数
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    # 有学生档案的用户数
    users_with_profile = User.objects.filter(student_profile__isnull=False).count()
    
    # 统计各状态申请数量
    status_stats = JobApplication.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 统计用户活动
    active_users_count = User.objects.filter(
        job_applications__isnull=False
    ).distinct().count()
    
    # 最近注册的用户
    recent_users = User.objects.order_by('-date_joined')[:10]
    
    # 最活跃的用户（按申请数量）
    most_active_users = User.objects.annotate(
        application_count=Count('job_applications')
    ).filter(application_count__gt=0).order_by('-application_count')[:10]
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'users_with_profile': users_with_profile,
        'status_stats': status_stats,
        'active_users_count': active_users_count,
        'recent_users': recent_users,
        'most_active_users': most_active_users,
    }
    
    return render(request, 'admin/user_statistics.html', context)
