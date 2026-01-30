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
        # 获取所有子页面（职位）- 直接使用 JobPage.objects 确保可以过滤 JobPage 字段
        job_pages = JobPage.objects.child_of(self).live()
        
        # 按类型筛选
        job_type = request.GET.get('job_type')
        if job_type:
            job_pages = job_pages.filter(job_type=job_type)
        
        # 关键词搜索（职位名称、公司、描述）
        search_query = request.GET.get('q')
        if search_query:
            job_pages = job_pages.filter(
                Q(job_title__icontains=search_query) |
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

    class Meta:
        verbose_name = "职位页面"
        verbose_name_plural = "职位页面"

    # 单个职位详情页使用 job_page.html 模板
    template = "jobs/job_page.html"


class JobIndexPage(Page):
    intro = RichTextField(blank=True, verbose_name="导语")
    
    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]
    
    # 指定该页面下只能添加 JobPage 类型的子页面
    subpage_types = ['jobs.JobPage']
    
    class Meta:
        verbose_name = "职位索引页面"
        verbose_name_plural = "职位索引页面"
    
    def get_context(self, request, *args, **kwargs):
        """职位列表页的上下文，包含搜索和筛选功能"""
        context = super().get_context(request, *args, **kwargs)
        from django.db.models import Q
        import re
        
        # 获取所有子页面（职位）- 直接使用 JobPage.objects 确保可以过滤 JobPage 字段
        job_pages = JobPage.objects.child_of(self).live()
        
        # 1. 关键词搜索（职位名称、公司名称、职位描述）
        search_query = request.GET.get('q', '').strip()
        if search_query:
            job_pages = job_pages.filter(
                Q(job_title__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # 2. 按职位类型筛选
        job_type = request.GET.get('job_type', '').strip()
        if job_type:
            job_pages = job_pages.filter(job_type=job_type)
        
        # 3. 按工作地点筛选（支持省市区分级筛选）
        province = request.GET.get('province', '').strip()
        city = request.GET.get('city', '').strip()
        district = request.GET.get('district', '').strip()
        
        if province or city or district:
            from .location_utils import parse_location
            location_query = Q()
            
            # 遍历所有职位，检查是否符合筛选条件
            filtered_job_ids = []
            for job in job_pages:
                job_province, job_city, job_district = parse_location(job.location)
                
                match = True
                
                if province:
                    if job_province != province:
                        match = False
                
                if match and city:
                    if job_city != city:
                        match = False
                
                if match and district:
                    if job_district != district:
                        match = False
                
                if match:
                    filtered_job_ids.append(job.id)
            
            if filtered_job_ids:
                job_pages = job_pages.filter(id__in=filtered_job_ids)
            else:
                job_pages = job_pages.none()
        
        # 4. 按薪资范围筛选
        salary_min = request.GET.get('salary_min', '').strip()
        salary_max = request.GET.get('salary_max', '').strip()
        
        if salary_min or salary_max:
            # 解析薪资字符串，提取数字范围
            # 支持格式：8-12K, 8K-12K, 8000-12000, 8万-12万等
            def parse_salary(salary_str):
                """解析薪资字符串，返回最小值和最大值（单位：元）"""
                if not salary_str:
                    return None, None
                
                # 移除空格
                salary_str = salary_str.replace(' ', '')
                
                # 处理"面议"等特殊情况
                if '面议' in salary_str or 'negotiable' in salary_str.lower():
                    return None, None
                
                # 提取数字和单位
                # 匹配模式：数字-数字K/万/元
                pattern = r'(\d+(?:\.\d+)?)\s*[-~至]\s*(\d+(?:\.\d+)?)\s*([Kk万万千]?)|(\d+(?:\.\d+)?)\s*([Kk万万千]?)以上|(\d+(?:\.\d+)?)\s*([Kk万万千]?)以下'
                match = re.search(pattern, salary_str)
                
                if match:
                    if match.group(1) and match.group(2):  # 范围格式：8-12K
                        min_val = float(match.group(1))
                        max_val = float(match.group(2))
                        unit = match.group(3) or ''
                        
                        # 转换为元
                        if '万' in unit or 'w' in unit.lower():
                            min_val *= 10000
                            max_val *= 10000
                        elif 'K' in unit or 'k' in unit or '千' in unit:
                            min_val *= 1000
                            max_val *= 1000
                        
                        return int(min_val), int(max_val)
                    elif match.group(4):  # 单个数字格式
                        val = float(match.group(4))
                        unit = match.group(5) or ''
                        
                        if '万' in unit or 'w' in unit.lower():
                            val *= 10000
                        elif 'K' in unit or 'k' in unit or '千' in unit:
                            val *= 1000
                        
                        return int(val), int(val)
                    elif match.group(6):  # 以上格式
                        val = float(match.group(6))
                        unit = match.group(7) or ''
                        
                        if '万' in unit or 'w' in unit.lower():
                            val *= 10000
                        elif 'K' in unit or 'k' in unit or '千' in unit:
                            val *= 1000
                        
                        return int(val), None
                    elif match.group(8):  # 以下格式
                        val = float(match.group(8))
                        unit = match.group(9) or ''
                        
                        if '万' in unit or 'w' in unit.lower():
                            val *= 10000
                        elif 'K' in unit or 'k' in unit or '千' in unit:
                            val *= 1000
                        
                        return None, int(val)
                
                return None, None
            
            # 筛选符合条件的职位
            # 先将 QuerySet 转换为列表以便逐个检查薪资
            job_list = list(job_pages)
            filtered_job_ids = []
            
            for job in job_list:
                job_min, job_max = parse_salary(job.salary)
                
                # 如果职位没有薪资信息
                if job_min is None and job_max is None:
                    # 如果用户指定了薪资要求，则排除没有薪资信息的职位
                    # 如果用户没有指定薪资要求，则包含该职位
                    if not salary_min and not salary_max:
                        filtered_job_ids.append(job.id)
                    continue
                
                # 用户指定的最小薪资（单位：元）
                user_min = None
                if salary_min:
                    try:
                        user_min = int(float(salary_min) * 1000)  # 假设用户输入的是K为单位
                    except ValueError:
                        pass
                
                # 用户指定的最大薪资（单位：元）
                user_max = None
                if salary_max:
                    try:
                        user_max = int(float(salary_max) * 1000)  # 假设用户输入的是K为单位
                    except ValueError:
                        pass
                
                # 判断是否匹配
                match = True
                
                if user_min is not None:
                    # 用户要求最低薪资，职位最高薪资必须大于等于用户最低要求
                    if job_max is not None and job_max < user_min:
                        match = False
                    # 如果职位只有最低薪资，检查是否满足要求
                    elif job_max is None and job_min is not None and job_min < user_min:
                        match = False
                
                if user_max is not None and match:
                    # 用户要求最高薪资，职位最低薪资必须小于等于用户最高要求
                    if job_min is not None and job_min > user_max:
                        match = False
                
                if match:
                    filtered_job_ids.append(job.id)
            
            # 使用 id__in 来筛选符合条件的职位
            if filtered_job_ids:
                job_pages = job_pages.filter(id__in=filtered_job_ids)
            else:
                # 如果没有匹配的职位，返回空 QuerySet
                job_pages = job_pages.none()
        
        # 分页（每页15条，适合移动端）
        paginator = Paginator(job_pages, 15)
        page = request.GET.get('page')
        try:
            job_pages = paginator.page(page)
        except PageNotAnInteger:
            job_pages = paginator.page(1)
        except EmptyPage:
            job_pages = paginator.page(paginator.num_pages)
        
        # 获取省份列表，用于下拉选择
        from .location_utils import extract_provinces_from_jobs
        provinces = extract_provinces_from_jobs()
        
        # 添加到上下文
        context['job_pages'] = job_pages
        context['job_types'] = JobPage.JOB_TYPES  # 用于筛选标签
        context['provinces'] = provinces  # 用于省份下拉选择
        context['current_filters'] = {
            'q': search_query,
            'job_type': job_type,
            'province': province,
            'city': city,
            'district': district,
            'salary_min': salary_min,
            'salary_max': salary_max,
        }
        
        return context
    
    # 职位列表页使用 job_index_page.html 模板
    template = "jobs/job_index_page.html"


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
        
        # 基础查询：所有已发布的职位（使用.specific()确保加载具体类型）
        from django.db.models import Q
        all_jobs = JobPage.objects.live().specific()
        
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
        # 需要先转换为列表才能进行文本搜索，使用.specific()确保属性已加载
        major_jobs_list = list(major_jobs.specific())
        fresh_graduate_jobs = [job for job in major_jobs_list if '应届' in job.description or '毕业生' in job.description]
        other_jobs = [job for job in major_jobs_list if job not in fresh_graduate_jobs]
        
        # 组合结果：应届生职位在前，其他在后
        final_jobs = fresh_graduate_jobs + other_jobs
        
        # 去重并限制数量，同时确保所有职位都有有效的 slug
        seen_ids = set()
        unique_jobs = []
        for job in final_jobs:
            if job.id not in seen_ids:
                # 强制重新从数据库加载以确保所有属性（包括 slug）都被正确加载
                try:
                    reloaded_job = JobPage.objects.filter(pk=job.pk).live().specific().first()
                    if reloaded_job and reloaded_job.slug:
                        seen_ids.add(reloaded_job.id)
                        unique_jobs.append(reloaded_job)
                    elif reloaded_job and not reloaded_job.slug:
                        # 如果重新加载后仍然没有 slug，生成一个
                        from django.utils.text import slugify
                        # 尝试使用 unidecode 处理中文
                        company = reloaded_job.company_name or "未知公司"
                        title = reloaded_job.job_title or "未知职位"
                        try:
                            from unidecode import unidecode
                            company = unidecode(company)
                            title = unidecode(title)
                        except ImportError:
                            pass
                        base_slug = slugify(f"{company}-{title}")
                        if not base_slug or len(base_slug.strip()) == 0:
                            base_slug = f"job-{reloaded_job.id}"
                        # 确保唯一性
                        slug = base_slug
                        counter = 1
                        while JobPage.objects.filter(slug=slug).exclude(pk=reloaded_job.pk).exists():
                            slug = f"{base_slug}-{counter}"
                            counter += 1
                        reloaded_job.slug = slug
                        reloaded_job.save(update_fields=['slug'])
                        if reloaded_job.live:
                            reloaded_job.save_revision().publish()
                        seen_ids.add(reloaded_job.id)
                        unique_jobs.append(reloaded_job)
                except Exception as e:
                    # 如果重新加载失败，跳过这个职位
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"无法加载职位 {job.id}: {str(e)}")
                    pass
        
        recommendations = unique_jobs[:20]  # 最多推荐20个
        
        # 添加到上下文
        context['recommendations'] = recommendations
        context['profile'] = profile
        # 预处理偏好地点列表，供模板使用
        context['preferred_locations_list'] = preferred_locations
        
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
    
    phone = models.CharField(
        '联系电话',
        max_length=20,
        blank=True,
        help_text='手机号码'
    )
    
    avatar = models.ImageField(
        '头像',
        upload_to='student_avatars/%Y/%m/',
        blank=True,
        null=True,
        help_text='用户头像图片'
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
    
    @property
    def user_email(self):
        """获取用户邮箱"""
        return self.user.email if self.user else "-"
    
    def resume_status(self):
        """显示简历状态（用于列表页）"""
        if not self.resume:
            return "未上传"
        
        import os
        from django.utils.html import format_html
        from django.urls import reverse
        
        try:
            file_size = self.resume.size
            file_name = os.path.basename(self.resume.name)
            file_ext = os.path.splitext(file_name)[1].upper()
            
            # 格式化文件大小
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            
            # 生成下载链接
            download_url = reverse('admin_download_resume', args=[self.pk])
            
            html = f"""
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="color: #28a745; font-weight: bold;">✓ 已上传</span>
                <span style="color: #666; font-size: 12px;">{file_ext} · {size_str}</span>
                <a href="{download_url}" target="_blank" 
                   style="color: #007cba; text-decoration: none; font-size: 12px;"
                   title="下载简历">
                    <span style="margin-left: 4px;">📥</span>
                </a>
            </div>
            """
            return format_html(html)
        except Exception as e:
            return format_html('<span style="color: #dc3545;">文件错误</span>')
    
    resume_status.short_description = '简历状态'
    resume_status.admin_order_field = 'resume'
    
    @property
    def resume_info_display(self):
        """用于Wagtail后台显示的简历信息"""
        if not self.resume:
            return "未上传简历"
        
        import os
        from django.utils.html import format_html
        from django.urls import reverse
        
        try:
            file_size = self.resume.size
            file_name = os.path.basename(self.resume.name)
            file_ext = os.path.splitext(file_name)[1].upper()
            
            # 格式化文件大小
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            
            # 获取文件修改时间
            try:
                file_path = self.resume.path
                from datetime import datetime
                mtime = os.path.getmtime(file_path)
                upload_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            except:
                upload_time = "未知"
            
            download_url = reverse('admin_download_resume', args=[self.pk])
            
            html = f"""
            <div style="padding: 15px; background-color: #f9f9f9; border-radius: 5px; margin: 10px 0;">
                <h4 style="margin-top: 0; margin-bottom: 12px;">简历文件信息</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold; width: 120px;">文件名：</td>
                        <td style="padding: 8px; word-break: break-all;">{file_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">文件类型：</td>
                        <td style="padding: 8px;"><span style="color: #007cba; font-weight: bold;">{file_ext}</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">文件大小：</td>
                        <td style="padding: 8px;"><span style="color: #28a745; font-weight: bold;">{size_str}</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">上传时间：</td>
                        <td style="padding: 8px;">{upload_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">操作：</td>
                        <td style="padding: 8px;">
                            <a href="{download_url}" target="_blank" 
                               style="display: inline-block; padding: 6px 12px; background-color: #007cba; 
                                      color: white; text-decoration: none; border-radius: 4px; font-size: 13px;">
                                📥 下载简历
                            </a>
                            {f'<a href="{self.resume.url}" target="_blank" style="display: inline-block; margin-left: 8px; padding: 6px 12px; background-color: #28a745; color: white; text-decoration: none; border-radius: 4px; font-size: 13px;">👁️ 预览</a>' if hasattr(self.resume, 'url') else ''}
                        </td>
                    </tr>
                </table>
            </div>
            """
            return format_html(html)
        except Exception as e:
            return format_html(f'<div style="color: #dc3545;">无法加载简历信息: {str(e)}</div>')
    
    @property
    def user_full_name(self):
        """获取用户全名"""
        if self.user:
            name = f"{self.user.first_name} {self.user.last_name}".strip()
            return name or self.user.username
        return "-"
    
    def get_activity_summary(self):
        """获取活动统计摘要"""
        try:
            # JobApplication 在文件后面定义，使用字符串引用避免循环导入
            from django.apps import apps
            JobApplication = apps.get_model('jobs', 'JobApplication')
            applications = JobApplication.objects.filter(user=self.user)
            saved = applications.filter(status='saved').count()
            applied = applications.filter(status='applied').count()
            return f"收藏: {saved} | 申请: {applied}"
        except Exception:
            return "-"



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

