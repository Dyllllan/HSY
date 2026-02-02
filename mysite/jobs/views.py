from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
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
def profile_page(request):
    """用户个人中心页面"""
    user = request.user
    
    # 获取或创建学生档案
    profile, created = StudentProfile.objects.get_or_create(user=user)
    
    # 获取用户的职位申请记录
    user_applications = JobApplication.objects.filter(user=user)
    
    # 统计信息
    applied_count = user_applications.filter(status='applied').count()  # 已投递
    pending_interview_count = user_applications.filter(status__in=['contacted', 'applied']).count()  # 待面试（已申请或已联系状态）
    
    # 计算平均竞争力（简单算法：基于申请成功率）
    total_applications = user_applications.count()
    accepted_count = user_applications.filter(status='accepted').count()
    if total_applications > 0:
        competitiveness = int((accepted_count / total_applications) * 100)
    else:
        competitiveness = 92  # 默认值
    
    # 计算毕业年份标签
    graduation_label = f"{profile.graduation_year}届准毕业生"
    
    return render(request, 'jobs/account/profile.html', {
        'profile': profile,
        'user': user,
        'applied_count': applied_count,
        'pending_interview_count': pending_interview_count,
        'competitiveness': competitiveness,
        'graduation_label': graduation_label,
    })


@login_required
def saved_jobs_list(request):
    """收藏职位列表页面"""
    user = request.user
    
    # 获取用户收藏的所有职位
    saved_applications = JobApplication.objects.filter(
        user=user,
        status='saved'
    ).select_related('job_page').order_by('-created_at')
    
    # 分页
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(saved_applications, 15)
    page = request.GET.get('page')
    try:
        saved_applications = paginator.page(page)
    except PageNotAnInteger:
        saved_applications = paginator.page(1)
    except EmptyPage:
        saved_applications = paginator.page(paginator.num_pages)
    
    return render(request, 'jobs/account/saved_jobs_list.html', {
        'saved_applications': saved_applications,
        'total_count': paginator.count,
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
            return redirect('account_profile')
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

def ai_career_navigation(request):
    """AI职场导航页面"""
    return render(request, 'jobs/ai_career_navigation.html')

@login_required
def upload_resume_api(request):
    """API: 上传简历文件"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持POST请求'})
    
    if 'resume' not in request.FILES:
        return JsonResponse({'success': False, 'message': '请选择文件'})
    
    file = request.FILES['resume']
    
    # 验证文件类型
    valid_extensions = ['.pdf', '.docx']
    file_name = file.name.lower()
    if not any(file_name.endswith(ext) for ext in valid_extensions):
        return JsonResponse({'success': False, 'message': '仅支持 PDF 或 DOCX 格式'})
    
    # 验证文件大小（10MB）
    if file.size > 10 * 1024 * 1024:
        return JsonResponse({'success': False, 'message': '文件大小不能超过 10MB'})
    
    # 保存文件到用户档案
    import os
    from datetime import datetime
    
    try:
        profile, created = StudentProfile.objects.get_or_create(user=request.user)
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_ext = os.path.splitext(file.name)[1]
        file_name = f'resume_{request.user.id}_{timestamp}{file_ext}'
        
        # 保存文件
        profile.resume.save(file_name, file, save=True)
        file_path = profile.resume.name
        
        # 返回文件ID（使用文件路径作为ID）
        return JsonResponse({
            'success': True,
            'file_id': file_path,
            'message': '文件上传成功'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'文件保存失败: {str(e)}'
        })

@login_required
def analyze_resume_api(request):
    """API: AI分析简历"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持POST请求'})
    
    import json
    data = json.loads(request.body)
    file_id = data.get('file_id')
    
    if not file_id:
        return JsonResponse({'success': False, 'message': '缺少文件ID'})
    
    # 获取文件
    from django.core.files.storage import default_storage
    from django.conf import settings
    import os
    
    try:
        # 构建完整文件路径
        file_path = os.path.join(settings.MEDIA_ROOT, file_id)
        if not os.path.exists(file_path):
            return JsonResponse({'success': False, 'message': '文件不存在'})
        file = open(file_path, 'rb')
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'文件读取失败: {str(e)}'})
    
    # 调用AI分析接口（这里需要实现实际的AI分析逻辑）
    # 目前返回模拟数据
    try:
        report = generate_ai_report(file, request.user)
        file.close()
        
        # 保存分析结果到用户档案
        try:
            profile, created = StudentProfile.objects.get_or_create(user=request.user)
            profile.ai_report = report
            profile.ai_report_updated_at = timezone.now()
            profile.save()
        except Exception as e:
            print(f'保存AI报告失败: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'report': report,
            'message': '分析完成'
        })
    except Exception as e:
        file.close()
        return JsonResponse({
            'success': False,
            'message': f'分析失败: {str(e)}'
        })

@login_required
def upload_avatar_api(request):
    """API: 上传头像"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持POST请求'})
    
    if 'avatar' not in request.FILES:
        return JsonResponse({'success': False, 'message': '请选择图片'})
    
    file = request.FILES['avatar']
    
    # 验证文件类型
    valid_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in valid_types:
        return JsonResponse({'success': False, 'message': '仅支持 JPG、PNG、GIF 或 WebP 格式'})
    
    # 验证文件大小（5MB）
    if file.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'message': '图片大小不能超过 5MB'})
    
    # 保存头像
    try:
        profile, created = StudentProfile.objects.get_or_create(user=request.user)
        profile.avatar = file
        profile.save()
        
        return JsonResponse({
            'success': True,
            'avatar_url': profile.avatar.url if profile.avatar else '',
            'message': '头像上传成功'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'上传失败: {str(e)}'
        })
    except Exception as e:
        file.close()
        return JsonResponse({
            'success': False,
            'message': f'分析失败: {str(e)}'
        })

def generate_ai_report(file, user):
    """生成AI报告（需要集成实际的AI API）"""
    # TODO: 集成实际的AI API
    # 这里返回一个示例报告
    
    # 尝试读取文件内容（简化处理）
    file_name = file.name.lower()
    
    report = f"""【AI职场竞争力报告】

根据您的简历分析，以下是您的职场竞争力评估：

📊 基本信息分析
文件类型: {file_name.split('.')[-1].upper()}
分析时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

💼 技能匹配度
技术技能: 85分
软技能: 78分
综合匹配度: 82分

🎯 岗位推荐
基于您的简历内容，我们为您推荐以下类型的岗位：
1. 前端开发工程师
2. 后端开发工程师
3. 全栈开发工程师

💡 提升建议
1. 加强项目经验的描述
2. 突出核心技能和成果
3. 完善教育背景信息

📈 竞争力排名
在同类求职者中，您的竞争力排名：前30%

注：此报告基于AI自动分析生成，仅供参考。实际匹配度可能因具体岗位要求而有所不同。
"""
    
    return report

@login_required
def ai_result_page(request):
    """AI分析结果页面"""
    user = request.user
    
    # 获取学生档案
    try:
        profile = user.student_profile
    except StudentProfile.DoesNotExist:
        profile = None
    
    # 获取AI分析报告
    ai_report = None
    report_updated_at = None
    has_report = False
    
    if profile:
        ai_report = profile.ai_report
        report_updated_at = profile.ai_report_updated_at
        has_report = bool(ai_report and ai_report.strip())
    
    return render(request, 'jobs/ai_result.html', {
        'profile': profile,
        'user': user,
        'ai_report': ai_report,
        'report_updated_at': report_updated_at,
        'has_report': has_report,
    })

# Create your views here.
