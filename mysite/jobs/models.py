from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel,MultiFieldPanel
from django.conf import settings
from django.utils import timezone
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


class JobIndexPage(Page):
    intro = RichTextField(blank=True, verbose_name="导语")
    
    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]
    
    # 指定该页面下只能添加 JobPage 类型的子页面
    subpage_types = ['jobs.JobPage']


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
