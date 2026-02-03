from django.db import models

from wagtail.models import Page


class HomePage(Page):
    # 定义分类关键词配置（类属性，避免重复定义）
    # 优化后的关键词配置：更精确，减少误匹配
    CATEGORY_KEYWORDS_CONFIG = {
        '互联网': {
            # 优先匹配职位名称中的关键词，避免过于宽泛的词
            'keywords': [
                # 核心行业词
                '互联网', 'IT', '软件', '科技', '计算机', '信息',
                # 技术岗位（优先匹配职位名称）
                '程序员', '开发工程师', '前端工程师', '后端工程师', '算法工程师', 
                '测试工程师', '运维工程师', 'DevOps', '架构师', '全栈工程师',
                # 技术栈（仅在职位名称中匹配）
                'Python开发', 'Java开发', 'JavaScript开发', 'React开发', 'Vue开发', 
                'Node.js', 'Go开发', 'C++开发', 'Android开发', 'iOS开发',
                # 互联网特有岗位
                '产品经理', '产品运营', '互联网运营', '数据分析师', '数据工程师',
                'UI设计师', 'UX设计师', '交互设计师', 'Web前端', '移动端开发',
                # 互联网公司常见词
                '云计算', '大数据', '人工智能', 'AI算法', '机器学习', '深度学习',
                '网站开发', 'APP开发', '小程序开发', '平台开发', '系统开发'
            ],
            'job_types': ['intern', 'fulltime'],
        },
        '金融': {
            'keywords': [
                # 金融行业核心词
                '金融', '银行', '证券', '基金', '保险', '投资', '理财',
                # 金融岗位
                '金融分析师', '投资顾问', '理财师', '风控', '信贷', '审计',
                '财务分析', '量化交易', '投行', '券商', '信托', '期货',
                # 金融相关
                '支付', '交易', '外汇', '债券', '股票', '资产', '财富管理',
                '融资', '贷款', '会计', '财务'
            ],
            'job_types': ['fulltime'],
        },
        '教育': {
            'keywords': [
                # 教育行业核心词
                '教育', '培训', '教师', '讲师', '教学', '课程', '学习',
                # 教育岗位
                '教育培训', '在线教育', 'K12教育', '职业教育', '大学教师',
                '学校', '教育机构', '教研', '教务', '招生', '教育运营',
                # 教育相关
                '辅导', '家教', '课程设计', '教育产品'
            ],
            'job_types': ['fulltime', 'parttime'],
        },
        '艺术': {
            'keywords': [
                # 艺术设计核心词（避免与建筑、互联网设计混淆）
                '艺术', '美术', '创意设计', '视觉设计', '平面设计',
                # 艺术岗位
                '插画师', '原画师', '动画师', '视频剪辑', '影视后期',
                '摄影师', '摄像师', '导演', '编剧', '音乐', '舞蹈', '表演',
                # 艺术相关（避免与UI/UX混淆）
                '广告设计', '品牌设计', '包装设计', '3D建模', '渲染',
                '媒体', '艺术创作'
            ],
            'job_types': ['fulltime', 'parttime'],
        },
        '建筑': {
            'keywords': [
                # 建筑行业核心词
                '建筑', '工程', '施工', '建筑规划', '结构', '土木',
                # 建筑岗位
                '建筑师', '结构工程师', '土木工程师', '造价', '监理',
                '项目经理', 'CAD', 'BIM', '装修', '装饰', '景观设计',
                '园林', '室内设计', '城市规划', '房地产', '地产开发',
                # 建筑相关（避免与艺术设计混淆）
                '建筑工程', '施工管理', '工程管理'
            ],
            'job_types': ['fulltime'],
        },
        '医疗': {
            'keywords': [
                # 医疗行业核心词
                '医疗', '医院', '医生', '护士', '护理', '医学', '临床',
                # 医疗岗位
                '临床医生', '临床护士', '药学', '生物医学', '健康管理',
                '康复', '中医', '西医', '诊断', '治疗', '医疗器械',
                '医药', '制药', '检验', '影像', '病理'
            ],
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
                if category == '推荐':
                    # 处理"推荐"分类：根据AI报告中的岗位推荐筛选
                    if request.user.is_authenticated:
                        try:
                            from jobs.models import StudentProfile
                            from jobs.report_parser import parse_ai_report
                            profile = getattr(request.user, 'student_profile', None)
                            if profile and profile.ai_report and profile.ai_report.strip():
                                # 解析AI报告
                                parsed_report = parse_ai_report(profile.ai_report)
                                job_recommendations = parsed_report.get('job_recommendations', [])
                                
                                if job_recommendations:
                                    # 根据推荐的岗位名称构建查询条件
                                    recommendation_query = Q()
                                    for rec in job_recommendations:
                                        job_name = rec.get('name', '').strip()
                                        if job_name:
                                            # 提取岗位名称中的关键词（去除常见后缀）
                                            keywords = [job_name]
                                            # 如果包含"岗位"、"职位"等后缀，也尝试去掉后缀匹配
                                            if '岗位' in job_name:
                                                keywords.append(job_name.replace('岗位', '').strip())
                                            if '职位' in job_name:
                                                keywords.append(job_name.replace('职位', '').strip())
                                            if '工作' in job_name:
                                                keywords.append(job_name.replace('工作', '').strip())
                                            
                                            for keyword in keywords:
                                                if keyword:
                                                    recommendation_query |= (
                                                        Q(job_title__icontains=keyword) |
                                                        Q(description__icontains=keyword)
                                                    )
                                    
                                    if recommendation_query:
                                        jobs = jobs.filter(recommendation_query)
                                    else:
                                        # 如果没有匹配的推荐，返回空结果
                                        jobs = jobs.none()
                                else:
                                    # 如果没有岗位推荐，返回空结果
                                    jobs = jobs.none()
                            else:
                                # 用户没有AI报告，返回空结果
                                jobs = jobs.none()
                        except Exception as e:
                            # 如果解析失败，返回空结果
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"解析AI报告失败: {str(e)}")
                            jobs = jobs.none()
                    else:
                        # 未登录用户，返回空结果
                        jobs = jobs.none()
                elif category in self.CATEGORY_KEYWORDS_CONFIG:
                    cat_config = self.CATEGORY_KEYWORDS_CONFIG[category]
                    # 改进的匹配逻辑：优先匹配职位名称，减少误匹配
                    keyword_query = Q()
                    
                    # 定义只在职位名称中匹配的关键词（技术栈、具体岗位等）
                    title_only_keywords = [
                        '开发工程师', '前端工程师', '后端工程师', '算法工程师', 
                        '测试工程师', '运维工程师', '架构师', '全栈工程师',
                        'Python开发', 'Java开发', 'JavaScript开发', 'React开发', 
                        'Vue开发', 'Node.js', 'Go开发', 'C++开发', 'Android开发', 
                        'iOS开发', '产品经理', '产品运营', '互联网运营', 
                        '数据分析师', '数据工程师', 'UI设计师', 'UX设计师', 
                        '交互设计师', 'Web前端', '移动端开发', '网站开发', 
                        'APP开发', '小程序开发', '平台开发', '系统开发',
                        '金融分析师', '投资顾问', '理财师', '量化交易',
                        '教育培训', '在线教育', 'K12教育', '职业教育', 
                        '大学教师', '教育机构', '教育运营', '课程设计', 
                        '教育产品', '插画师', '原画师', '动画师', '视频剪辑',
                        '影视后期', '摄影师', '摄像师', '建筑师', '结构工程师',
                        '土木工程师', '临床医生', '临床护士', '生物医学'
                    ]
                    
                    for keyword in cat_config['keywords']:
                        # 如果关键词在title_only_keywords中，只在职位名称中匹配
                        if keyword in title_only_keywords:
                            keyword_query |= Q(job_title__icontains=keyword)
                        else:
                            # 其他关键词优先匹配职位名称和公司名称，描述作为补充
                            # 优先匹配：职位名称权重最高
                            keyword_query |= (
                                Q(job_title__icontains=keyword) |
                                Q(company_name__icontains=keyword) |
                                Q(description__icontains=keyword)
                            )
                    
                    # 使用关键词匹配
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
            
            # 计算"推荐"分类的数量（仅当用户有AI报告时）
            recommendation_count = 0
            if request.user.is_authenticated:
                try:
                    from jobs.models import StudentProfile
                    from jobs.report_parser import parse_ai_report
                    profile = getattr(request.user, 'student_profile', None)
                    if profile and profile.ai_report and profile.ai_report.strip():
                        parsed_report = parse_ai_report(profile.ai_report)
                        job_recommendations = parsed_report.get('job_recommendations', [])
                        
                        if job_recommendations:
                            recommendation_query = Q()
                            for rec in job_recommendations:
                                job_name = rec.get('name', '').strip()
                                if job_name:
                                    keywords = [job_name]
                                    if '岗位' in job_name:
                                        keywords.append(job_name.replace('岗位', '').strip())
                                    if '职位' in job_name:
                                        keywords.append(job_name.replace('职位', '').strip())
                                    if '工作' in job_name:
                                        keywords.append(job_name.replace('工作', '').strip())
                                    
                                    for keyword in keywords:
                                        if keyword:
                                            recommendation_query |= (
                                                Q(job_title__icontains=keyword) |
                                                Q(description__icontains=keyword)
                                            )
                            
                            if recommendation_query:
                                recommendation_count = all_jobs_for_count.filter(recommendation_query).count()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"计算推荐岗位数量失败: {str(e)}")
            
            category_counts['推荐'] = recommendation_count
            
            # 如果职位数量较少，使用精确计算；否则使用估算
            if total_count < 1000:
                # 定义只在职位名称中匹配的关键词（与筛选逻辑保持一致）
                title_only_keywords = [
                    '开发工程师', '前端工程师', '后端工程师', '算法工程师', 
                    '测试工程师', '运维工程师', '架构师', '全栈工程师',
                    'Python开发', 'Java开发', 'JavaScript开发', 'React开发', 
                    'Vue开发', 'Node.js', 'Go开发', 'C++开发', 'Android开发', 
                    'iOS开发', '产品经理', '产品运营', '互联网运营', 
                    '数据分析师', '数据工程师', 'UI设计师', 'UX设计师', 
                    '交互设计师', 'Web前端', '移动端开发', '网站开发', 
                    'APP开发', '小程序开发', '平台开发', '系统开发',
                    '金融分析师', '投资顾问', '理财师', '量化交易',
                    '教育培训', '在线教育', 'K12教育', '职业教育', 
                    '大学教师', '教育机构', '教育运营', '课程设计', 
                    '教育产品', '插画师', '原画师', '动画师', '视频剪辑',
                    '影视后期', '摄影师', '摄像师', '建筑师', '结构工程师',
                    '土木工程师', '临床医生', '临床护士', '生物医学'
                ]
                
                for cat_name, cat_config in self.CATEGORY_KEYWORDS_CONFIG.items():
                    keyword_query = Q()
                    for keyword in cat_config['keywords']:
                        # 与筛选逻辑保持一致：某些关键词只在职位名称中匹配
                        if keyword in title_only_keywords:
                            keyword_query |= Q(job_title__icontains=keyword)
                        else:
                            keyword_query |= (
                                Q(job_title__icontains=keyword) |
                                Q(company_name__icontains=keyword) |
                                Q(description__icontains=keyword)
                            )
                    # 使用改进后的关键词匹配计算数量
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
            # 初始化所有分类的count为0（包括推荐）
            context['category_counts'] = {cat: 0 for cat in self.CATEGORY_KEYWORDS_CONFIG.keys()}
            context['category_counts']['推荐'] = 0
        
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
