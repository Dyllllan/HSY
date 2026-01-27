from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from wagtail.models import Page
from .models import JobPage, StudentProfile

@login_required
def personalized_recommendations(request):
    """基于学生档案的个性化职位推荐"""
    user = request.user
    
    # 获取学生档案（确保已创建）
    try:
        profile = user.student_profile
    except StudentProfile.DoesNotExist:
        # 如果档案不存在，重定向到完善信息页面
        from django.shortcuts import redirect
        return redirect('complete_profile')
    
    # 基础查询：所有已发布的职位
    all_jobs = Page.objects.type(JobPage).live().specific()
    
    # 规则1：按偏好职位类型筛选
    preferred_types = profile.get_preferred_job_types_list()
    if preferred_types:
        type_filter = Q(job_type__in=preferred_types)
        type_jobs = all_jobs.filter(type_filter)
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
    fresh_graduate_jobs = major_jobs.filter(description__icontains='应届') | major_jobs.filter(description__icontains='毕业生')
    
    # 组合结果：应届生职位在前，其他在后
    final_jobs = list(fresh_graduate_jobs) + [job for job in major_jobs if job not in fresh_graduate_jobs]
    
    # 去重并限制数量
    seen_ids = set()
    unique_jobs = []
    for job in final_jobs:
        if job.id not in seen_ids:
            seen_ids.add(job.id)
            unique_jobs.append(job)
    
    recommendations = unique_jobs[:20]  # 最多推荐20个
    
    return render(request, 'jobs/recommendations.html', {
        'recommendations': recommendations,
        'profile': profile,
    })
# Create your views here.
