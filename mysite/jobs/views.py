from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from wagtail.models import Page
from .models import JobPage, StudentProfile, JobApplication
from .forms import CustomSignupForm
from .location_utils import extract_provinces_from_jobs, extract_cities_from_jobs, extract_districts_from_jobs

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
    
    # 基础查询：所有已发布的职位 - 直接使用 JobPage.objects 确保可以过滤 JobPage 字段
    all_jobs = JobPage.objects.live()
    
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


@login_required
def dashboard(request):
    """用户工作台/个人档案页面"""
    user = request.user
    
    # 获取或创建学生档案
    profile, created = StudentProfile.objects.get_or_create(user=user)
    
    # 获取用户的职位申请记录
    user_applications = JobApplication.objects.filter(user=user)
    
    # 统计信息
    saved_count = user_applications.filter(status='saved').count()
    applied_count = user_applications.filter(status='applied').count()
    
    # 计算匹配度（简单算法：基于收藏和申请的比例）
    total_jobs = JobPage.objects.live().count()
    match_rate = min(100, int((saved_count + applied_count) / max(1, total_jobs) * 100)) if total_jobs > 0 else 0
    
    # 获取收藏和申请的记录
    saved_applications = user_applications.filter(status='saved').select_related('job_page')[:10]
    applied_applications = user_applications.filter(status='applied').select_related('job_page')[:10]
    
    return render(request, 'account/dashboard.html', {
        'profile': profile,
        'saved_count': saved_count,
        'applied_count': applied_count,
        'match_rate': match_rate,
        'saved_applications': saved_applications,
        'applied_applications': applied_applications,
    })


@login_required
def edit_profile(request):
    """编辑个人档案页面"""
    from .forms import ProfileEditForm
    
    user = request.user
    
    # 获取或创建学生档案
    profile, created = StudentProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, '个人档案已更新！')
            return redirect('dashboard')
    else:
        form = ProfileEditForm(instance=profile, user=user)
    
    return render(request, 'jobs/account/edit_profile.html', {
        'form': form,
        'profile': profile,
    })


def get_location_data(request):
    """API视图：获取省市区级联数据"""
    level = request.GET.get('level', 'province')  # province, city, district
    province = request.GET.get('province', '')
    city = request.GET.get('city', '')
    
    if level == 'province':
        provinces = extract_provinces_from_jobs()
        return JsonResponse({'data': provinces})
    
    elif level == 'city':
        cities = extract_cities_from_jobs(province=province if province else None)
        return JsonResponse({'data': cities})
    
    elif level == 'district':
        districts = extract_districts_from_jobs(
            province=province if province else None,
            city=city if city else None
        )
        return JsonResponse({'data': districts})
    
    return JsonResponse({'data': []})
# Create your views here.
