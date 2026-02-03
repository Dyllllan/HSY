from django.db import models

from wagtail.models import Page


class HomePage(Page):
    # 定义分类关键词配置（类属性，避免重复定义）
    CATEGORY_KEYWORDS_CONFIG = {
        '互联网': {
            'keywords': ['互联网', 'IT', '软件', '开发', '程序员', '前端', '后端', '算法', '数据', '产品', '运营', 'UI', 'UX', '测试', '运维', 'DevOps', 'Python', 'Java', 'JavaScript', 'React', 'Vue', 'Node', 'Go', 'C++', 'Android', 'iOS', '移动端', 'Web', '全栈', '架构师', '技术', '计算机', '信息', '科技', '网络', '系统', '平台', '应用', '网站', 'APP', '小程序', '云计算', '大数据', '人工智能', 'AI', '机器学习', '深度学习'],
            'job_types': ['intern', 'fulltime'],
        },
        '金融': {
            'keywords': ['金融', '银行', '证券', '基金', '保险', '投资', '理财', '财务', '会计', '审计', '风控', '信贷', '支付', '交易', '量化', '分析师', '投行', '券商', '信托', '期货', '外汇', '债券', '股票', '资产', '财富', '融资', '贷款'],
            'job_types': ['fulltime'],
        },
        '教育': {
            'keywords': ['教育', '培训', '教师', '讲师', '教学', '课程', '学习', '辅导', '在线教育', 'K12', '职业教育', '大学', '学校', '机构', '教研', '教务', '招生', '运营', '内容', '产品'],
            'job_types': ['fulltime', 'parttime'],
        },
        '艺术': {
            'keywords': ['艺术', '设计', '美术', '创意', '视觉', '平面', 'UI设计', 'UX设计', '交互', '动画', '视频', '影视', '媒体', '广告', '品牌', '包装', '插画', '原画', '3D', '建模', '渲染', '剪辑', '后期', '摄影', '摄像', '导演', '编剧', '音乐', '舞蹈', '表演'],
            'job_types': ['fulltime', 'parttime'],
        },
        '建筑': {
            'keywords': ['建筑', '工程', '施工', '设计', '规划', '结构', '土木', '造价', '监理', '项目经理', '建筑师', '工程师', 'CAD', 'BIM', '装修', '装饰', '景观', '园林', '室内设计', '城市规划', '房地产', '地产', '开发'],
            'job_types': ['fulltime'],
        },
        '医疗': {
            'keywords': ['医疗', '医院', '医生', '护士', '护理', '医学', '临床', '药学', '生物', '健康', '康复', '中医', '西医', '诊断', '治疗', '医疗器械', '医药', '制药', '检验', '影像', '病理'],
            'job_types': ['fulltime', 'parttime'],
        },
    }
    
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # 获取职位数据
        from jobs.models import JobPage, JobIndexPage
        from django.db.models import Q
        
        # 查找 JobIndexPage
        job_index = JobIndexPage.objects.live().first()
        if job_index:
            # 获取所有职位
            jobs = JobPage.objects.child_of(job_index).live().specific()
            
            # 1. 处理搜索关键词
            search_query = request.GET.get('q', '').strip()
            if search_query:
                jobs = jobs.filter(
                    Q(job_title__icontains=search_query) |
                    Q(company_name__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(location__icontains=search_query)
                )
            
            # 2. 处理分类筛选
            category = request.GET.get('category', '').strip()
            if category:
                if category in self.CATEGORY_KEYWORDS_CONFIG:
                    cat_config = self.CATEGORY_KEYWORDS_CONFIG[category]
                    # 构建查询条件
                    keyword_query = Q()
                    for keyword in cat_config['keywords']:
                        keyword_query |= (
                            Q(job_title__icontains=keyword) |
                            Q(company_name__icontains=keyword) |
                            Q(description__icontains=keyword)
                        )
                    
                    # 只使用关键词匹配，不限制职位类型，提高匹配率
                    jobs = jobs.filter(keyword_query)
                else:
                    # 如果不在映射中，尝试在描述中搜索
                    jobs = jobs.filter(
                        Q(description__icontains=category) |
                        Q(job_title__icontains=category) |
                        Q(company_name__icontains=category)
                    )
            
            # 3. 限制显示数量（如果有搜索或筛选，显示所有结果；否则显示前10条）
            if search_query or category:
                jobs = jobs[:50]  # 搜索结果最多显示50条
            else:
                jobs = jobs[:10]  # 默认显示10条热门职位
            
            # 为每个职位添加收藏状态（如果用户已登录）
            if request.user.is_authenticated:
                for job in jobs:
                    job.is_saved_by_user = job.is_saved_by_user(request.user)
            
            # 计算每个分类的职位数量（用于显示）
            category_counts = {}
            # 只在有职位数据时计算，避免不必要的查询
            all_jobs_for_count = JobPage.objects.child_of(job_index).live().specific()
            total_count = all_jobs_for_count.count()
            
            # 如果职位数量较少，使用精确计算；否则使用估算
            if total_count < 1000:
                for cat_name, cat_config in self.CATEGORY_KEYWORDS_CONFIG.items():
                    keyword_query = Q()
                    for keyword in cat_config['keywords']:
                        keyword_query |= (
                            Q(job_title__icontains=keyword) |
                            Q(company_name__icontains=keyword) |
                            Q(description__icontains=keyword)
                        )
                    # 只使用关键词匹配计算数量，不限制职位类型
                    count = all_jobs_for_count.filter(keyword_query).count()
                    category_counts[cat_name] = count
            else:
                # 如果职位数量很多，使用简化的估算方法
                # 基于职位类型分布估算
                intern_count = all_jobs_for_count.filter(job_type='intern').count()
                fulltime_count = all_jobs_for_count.filter(job_type='fulltime').count()
                parttime_count = all_jobs_for_count.filter(job_type='parttime').count()
                
                # 简单估算（可以根据实际情况调整比例）
                category_counts['互联网'] = int((intern_count + fulltime_count) * 0.4)
                category_counts['金融'] = int(fulltime_count * 0.15)
                category_counts['教育'] = int((fulltime_count + parttime_count) * 0.2)
                category_counts['艺术'] = int((fulltime_count + parttime_count) * 0.15)
                category_counts['建筑'] = int(fulltime_count * 0.1)
                category_counts['医疗'] = int(fulltime_count * 0.08)
            
            context['jobs'] = jobs
            context['search_query'] = search_query
            context['current_category'] = category
            context['category_counts'] = category_counts
        else:
            context['jobs'] = []
            context['search_query'] = ''
            context['current_category'] = ''
            # 初始化所有分类的count为0
            context['category_counts'] = {cat: 0 for cat in self.CATEGORY_KEYWORDS_CONFIG.keys()}
        
        # 检查用户是否已完成AI测评
        has_ai_report = False
        if request.user.is_authenticated:
            try:
                # 使用getattr安全获取student_profile，避免DoesNotExist异常
                from jobs.models import StudentProfile
                profile = getattr(request.user, 'student_profile', None)
                if profile:
                    if profile.ai_report and profile.ai_report.strip():
                        has_ai_report = True
            except Exception as e:
                # 如果出现任何异常，has_ai_report保持False
                pass
        
        context['has_ai_report'] = has_ai_report
        
        return context
