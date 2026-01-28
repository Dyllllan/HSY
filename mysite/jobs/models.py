from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel,MultiFieldPanel
from django.conf import settings
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from modelcluster.fields import ParentalKey
# Create your models here.
class JobPage(Page):
    # 基础信息
    company_name = models.CharField(max_length=255, verbose_name="公司名称")
    job_title = models.CharField(max_length=255, verbose_name="职位名称")
    location = models.CharField(max_length=100, verbose_name="工作地点")
    
    # 薪资可以用字符串灵活表示，如“8-12K”
    salary = models.CharField(max_length=100, verbose_name="薪资范围", blank=True)
    
    # 岗位详情，使用富文本字段方便格式化描述
    description = RichTextField(features=['bold', 'italic', 'link', 'ol', 'ul'], verbose_name="职位描述")
    
    # 分类标签
    JOB_TYPES = [
        ('intern', '实习'),
        ('fulltime', '全职'),
        ('parttime', '兼职'),
    ]
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='fulltime', verbose_name="职位类型")
    
    # 来源网站
    source_website = models.CharField(max_length=50, verbose_name="来源网站", default='智联招聘')
    source_url = models.URLField(verbose_name="原始链接", blank=True)
    
    # 管理后台编辑界面配置
    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('company_name'),
            FieldPanel('job_title'),
            FieldPanel('location'),
            FieldPanel('salary'),
        ], heading="基础信息"),
        FieldPanel('description'),
        MultiFieldPanel([
            FieldPanel('job_type'),
            FieldPanel('source_website'),
            FieldPanel('source_url'),
        ], heading="分类与来源"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        from django.db.models import Q
        # 获取所有子页面（职位）
        job_pages = self.get_children().live().specific()
        
        # 按类型筛选
        job_type = request.GET.get('job_type')
        if job_type:
            job_pages = job_pages.filter(job_type=job_type)
        
        # 关键词搜索（标题、公司、描述）
        search_query = request.GET.get('q')
        if search_query:
            job_pages = job_pages.filter(
                Q(title__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # 分页（每页15条，适合移动端）
        paginator = Paginator(job_pages, 15)
        page = request.GET.get('page')
        try:
            job_pages = paginator.page(page)
        except PageNotAnInteger:
            job_pages = paginator.page(1)
        except EmptyPage:
            job_pages = paginator.page(paginator.num_pages)
        
        # 添加到上下文
        context['job_pages'] = job_pages
        context['job_types'] = JobPage.JOB_TYPES  # 用于筛选标签
        return context

    @property
    def save_count(self):
        """收藏数量"""
        return self.applications.filter(status='saved').count()
    
    @property
    def apply_count(self):
        """申请数量"""
        return self.applications.filter(status='applied').count()
    
    def is_saved_by_user(self, user):
        """检查用户是否已收藏"""
        if not user.is_authenticated:
            return False
        return self.applications.filter(user=user, status='saved').exists()
    
    def is_applied_by_user(self, user):
        """检查用户是否已申请"""
        if not user.is_authenticated:
            return False
        return self.applications.filter(user=user, status='applied').exists()
        
template = "jobs/job_index_page.html"

class JobIndexPage(Page):
    intro = RichTextField(blank=True, verbose_name="导语")
    
    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]
    
    # 指定该页面下只能添加 JobPage 类型的子页面
    subpage_types = ['jobs.JobPage']


class RecommendationsPage(Page):
    """个性化推荐页面 - Wagtail页面模型"""
    intro = RichTextField(blank=True, verbose_name="页面介绍", help_text="显示在推荐列表上方的介绍文字")
    
    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]
    
    # 不允许添加子页面
    subpage_types = []
    
    class Meta:
        verbose_name = "个性化推荐页面"
        verbose_name_plural = "个性化推荐页面"
    
    def get_context(self, request, *args, **kwargs):
        """重写get_context方法，添加个性化推荐逻辑"""
        context = super().get_context(request, *args, **kwargs)
        
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            context['needs_login'] = True
            return context
        
        user = request.user
        
        # 获取学生档案
        try:
            profile = user.student_profile
        except StudentProfile.DoesNotExist:
            context['needs_profile'] = True
            return context
        
        # 基础查询：所有已发布的职位（直接使用JobPage模型）
        from django.db.models import Q
        all_jobs = JobPage.objects.live()
        
        # 规则1：按偏好职位类型筛选
        preferred_types = profile.get_preferred_job_types_list()
        if preferred_types:
            type_jobs = all_jobs.filter(job_type__in=preferred_types)
        else:
            type_jobs = all_jobs
        
        # 规则2：按偏好地点筛选（简单文本匹配）
        preferred_locations = [loc.strip() for loc in profile.preferred_locations.split(',') if loc.strip()]
        location_jobs = type_jobs
        if preferred_locations:
            # 构建地点查询：多个地点OR条件
            location_query = Q()
            for location in preferred_locations:
                location_query |= Q(location__icontains=location)
            location_jobs = type_jobs.filter(location_query)
        
        # 规则3：按专业匹配（从职位描述中匹配专业关键词）
        major_keywords = {
            'cs': ['计算机', '软件', '编程', '算法', '后端', '前端', '开发'],
            'se': ['软件工程', '测试', '运维', 'DevOps'],
            'ee': ['电子', '硬件', '电路', '嵌入式'],
            'business': ['商业', '市场', '营销', '管理'],
            'finance': ['金融', '财务', '会计', '投资'],
            'design': ['设计', 'UI', 'UX', '视觉', '平面']
        }
        
        major_jobs = location_jobs
        keywords = major_keywords.get(profile.major, [])
        if keywords:
            major_query = Q()
            for keyword in keywords:
                major_query |= Q(description__icontains=keyword) | Q(job_title__icontains=keyword)
            major_jobs = location_jobs.filter(major_query)
        
        # 规则4：应届生优先（标记为接受应届生的职位）
        # 需要先转换为列表才能进行文本搜索
        major_jobs_list = list(major_jobs)
        fresh_graduate_jobs = [job for job in major_jobs_list if '应届' in job.description or '毕业生' in job.description]
        other_jobs = [job for job in major_jobs_list if job not in fresh_graduate_jobs]
        
        # 组合结果：应届生职位在前，其他在后
        final_jobs = fresh_graduate_jobs + other_jobs
        
        # 去重并限制数量
        seen_ids = set()
        unique_jobs = []
        for job in final_jobs:
            if job.id not in seen_ids:
                seen_ids.add(job.id)
                unique_jobs.append(job)
        
        recommendations = unique_jobs[:20]  # 最多推荐20个
        
        # 添加到上下文
        context['recommendations'] = recommendations
        context['profile'] = profile
        
        return context
    
    template = "jobs/recommendations_page.html"


class StudentProfile(models.Model):
    # 与Wagtail用户一对一关联
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    
    # 学生基本信息
    student_id = models.CharField(
        '学号',
        max_length=20,
        blank=True,
        help_text='可选，用于身份验证'
    )
    
    SCHOOL_CHOICES = [
        ('tsinghua', '清华大学'),
        ('pku', '北京大学'),
        ('fudan', '复旦大学'),
        ('sjtu', '上海交通大学'),
        ('zju', '浙江大学'),
        ('other', '其他院校'),
    ]
    school = models.CharField(
        '学校',
        max_length=50,
        choices=SCHOOL_CHOICES,
        default='other'
    )
    
    MAJOR_CHOICES = [
        ('cs', '计算机科学'),
        ('se', '软件工程'),
        ('ee', '电子信息'),
        ('business', '工商管理'),
        ('finance', '金融学'),
        ('design', '设计艺术'),
        ('other', '其他专业'),
    ]
    major = models.CharField(
        '专业',
        max_length=50,
        choices=MAJOR_CHOICES,
        default='other'
    )
    
    graduation_year = models.IntegerField(
        '毕业年份',
        choices=[(year, str(year)) for year in range(2024, 2030)],
        default=2025
    )
    
    # 求职偏好（用于个性化推荐）
    preferred_job_types = models.CharField(
        '偏好职位类型',
        max_length=100,
        default='intern,fulltime',
        help_text='逗号分隔：intern(实习),fulltime(全职),parttime(兼职)'
    )
    
    preferred_locations = models.CharField(
        '偏好工作地点',
        max_length=200,
        default='北京,上海,深圳',
        help_text='逗号分隔的城市名'
    )
    
    # 简历信息
    resume = models.FileField(
        '简历',
        upload_to='student_resumes/%Y/%m/',
        blank=True,
        null=True
    )
    
    resume_text = models.TextField(
        '简历文本内容',
        blank=True,
        help_text='用于搜索匹配的简历文本'
    )
    
    # 状态与时间戳
    is_verified = models.BooleanField('已验证学生身份', default=False)
    last_active = models.DateTimeField('最后活跃时间', default=timezone.now)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '学生档案'
        verbose_name_plural = '学生档案'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_school_display()}"
    
    def get_preferred_job_types_list(self):
        """将偏好职位类型字符串转换为列表"""
        return [jt.strip() for jt in self.preferred_job_types.split(',') if jt.strip()]
    
    def update_last_active(self):
        """更新最后活跃时间"""
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])



class JobApplication(models.Model):
     STATUS_CHOICES = [
        ('saved', '已收藏'),
        ('applied', '已申请'),
        ('viewed', '已查看'),
        ('contacted', '已联系'),
        ('rejected', '已拒绝'),
        ('accepted', '已接受'),
    ]
    
     user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications'
    )
    
     job_page = ParentalKey(
        'jobs.JobPage',
        on_delete=models.CASCADE,
        related_name='applications'
    )
    
     status = models.CharField(
        '申请状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='saved'
    )
    
     applied_date = models.DateTimeField('申请时间', null=True, blank=True)
     notes = models.TextField('备注', blank=True)
    
    # 来源追踪
     source = models.CharField('来源', max_length=50, default='website')
     ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    
     created_at = models.DateTimeField('创建时间', auto_now_add=True)
     updated_at = models.DateTimeField('更新时间', auto_now=True)
    
     class Meta:
        unique_together = ['user', 'job_page']  # 防止重复收藏
        verbose_name = '职位申请'
        verbose_name_plural = '职位申请'
        ordering = ['-updated_at']
    
     def __str__(self):
        return f"{self.user.email} - {self.job_page.job_title}"
    
     def save(self, *args, **kwargs):
        # 如果是第一次申请，记录申请时间
        if self.status == 'applied' and not self.applied_date:
            self.applied_date = timezone.now()
        super().save(*args, **kwargs)

