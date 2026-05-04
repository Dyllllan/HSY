from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from wagtail.models import Page
import logging
from .models import JobPage, StudentProfile, JobApplication
from .forms import CustomSignupForm
from .location_utils import extract_provinces_from_jobs, extract_cities_from_jobs, extract_districts_from_jobs

logger = logging.getLogger(__name__)

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
    saved_count = user_applications.filter(is_saved=True).count()
    applied_count = user_applications.filter(applied_at__isnull=False).count()
    
    # 计算匹配度（简单算法：基于收藏和申请的比例）
    total_jobs = JobPage.objects.live().count()
    match_rate = min(100, int((saved_count + applied_count) / max(1, total_jobs) * 100)) if total_jobs > 0 else 0
    
    # 获取收藏和申请的记录
    saved_applications = user_applications.filter(is_saved=True).select_related('job_page')[:10]
    applied_applications = user_applications.filter(applied_at__isnull=False).select_related('job_page')[:10]
    
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
    # 注意：如果数据库迁移未运行，这里可能会报错
    # 请运行: python manage.py migrate
    try:
        profile, created = StudentProfile.objects.get_or_create(user=user)
    except Exception as e:
        # 如果字段不存在，提示用户运行迁移
        if 'ai_extracted_school' in str(e) or 'Unknown column' in str(e):
            messages.error(request, '数据库需要更新，请运行: python manage.py migrate')
            logger.error(f"数据库迁移未运行: {str(e)}")
            return render(request, 'jobs/account/profile.html', {
                'error': '数据库需要更新',
                'migration_needed': True,
                'user': user,
            })
        raise
    
    # 获取用户的职位申请记录
    user_applications = JobApplication.objects.filter(user=user)
    
    # 统计信息
    applied_count = user_applications.filter(applied_at__isnull=False).count()
    pending_interview_count = user_applications.filter(applied_at__isnull=False, status__in=["applied", "contacted"]).count()
    
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
        is_saved=True,
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
    """API: 上传简历文件并进行初步AI提取"""
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
    from .resume_parser import extract_text_from_resume
    from .resume_extractor import extract_resume_info
    from django.conf import settings
    from wagtail.documents.models import Document
    from .models import ResumePage, ResumeIndexPage
    
    try:
        profile, created = StudentProfile.objects.get_or_create(user=request.user)
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_ext = os.path.splitext(file.name)[1]
        file_name = f'resume_{request.user.id}_{timestamp}{file_ext}'
        
        # 保存文件
        profile.resume.save(file_name, file, save=True)
        file_path = os.path.join(settings.MEDIA_ROOT, profile.resume.name)
        
        # 提取简历文本
        resume_text = extract_text_from_resume(file_path)
        if resume_text:
            profile.resume_text = resume_text
            profile.save(update_fields=['resume_text'])
            
            # 进行AI初步提取
            extracted_info = extract_resume_info(resume_text)
            
            # 保存提取的信息
            profile.ai_extracted_school = extracted_info.get('school', '')
            profile.ai_extracted_major = extracted_info.get('major', '')
            profile.ai_extracted_internship_summary = extracted_info.get('internship_summary', '')
            profile.ai_extracted_hobbies = extracted_info.get('hobbies', '')
            profile.ai_extracted_skills = extracted_info.get('skills', [])
            profile.ai_extraction_completed = True
            profile.ai_extraction_updated_at = timezone.now()
            profile.save()
        
        # 同步到Wagtail管理系统
        try:
            # 1. 获取或创建简历索引页面
            resume_index = ResumeIndexPage.objects.live().first()
            if not resume_index:
                # 如果没有索引页面，尝试从根页面创建
                from wagtail.models import Page
                root = Page.get_first_root_node()
                if root:
                    resume_index = ResumeIndexPage(
                        title="简历管理",
                        slug="resumes"
                    )
                    root.add_child(instance=resume_index)
                    resume_index.save_revision().publish()
            
            # 2. 创建或更新简历页面
            resume_page = ResumePage.objects.filter(user_id=request.user.id).first()
            
            # 创建Wagtail Document（使用已保存的文件）
            document_title = f"{request.user.get_full_name() or request.user.username}的简历_{timestamp}"
            document = None
            
            # 检查是否已存在相同的文档
            existing_doc = Document.objects.filter(title=document_title).first()
            if existing_doc:
                document = existing_doc
            else:
                # 创建新文档，使用profile.resume文件
                document = Document(
                    title=document_title,
                    file=profile.resume
                )
                document.save()
            
            if resume_page:
                # 更新现有页面
                resume_page.title = f"{request.user.get_full_name() or request.user.username} - 简历"
                resume_page.student_name = request.user.get_full_name() or ''
                resume_page.student_email = request.user.email
                resume_page.resume_document = document
                resume_page.resume_text = resume_text or ''
                resume_page.ai_extracted_school = profile.ai_extracted_school
                resume_page.ai_extracted_major = profile.ai_extracted_major
                resume_page.ai_extracted_skills = profile.ai_extracted_skills or []
                resume_page.save()
                # 如果页面未发布，则发布
                if not resume_page.live:
                    resume_page.save_revision().publish()
                else:
                    resume_page.save_revision()
            else:
                # 创建新页面
                resume_page = ResumePage(
                    title=f"{request.user.get_full_name() or request.user.username} - 简历",
                    slug=f"resume-{request.user.id}-{timestamp}",
                    user_id=request.user.id,
                    student_name=request.user.get_full_name() or '',
                    student_email=request.user.email,
                    resume_document=document,
                    resume_text=resume_text or '',
                    ai_extracted_school=profile.ai_extracted_school,
                    ai_extracted_major=profile.ai_extracted_major,
                    ai_extracted_skills=profile.ai_extracted_skills or []
                )
                resume_index.add_child(instance=resume_page)
                resume_page.save_revision().publish()
        except Exception as wagtail_error:
            # Wagtail同步失败不影响主流程，只记录错误
            import traceback
            logger.warning(f"同步到Wagtail失败: {str(wagtail_error)}\n{traceback.format_exc()}")
    
        # 返回文件ID和提取状态
        return JsonResponse({
            'success': True,
            'file_id': profile.resume.name,
            'extraction_completed': profile.ai_extraction_completed,
            'message': '文件上传成功，AI提取完成' if resume_text else '文件上传成功'
        })
    except Exception as e:
        import traceback
        logger.error(f"上传简历失败: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'message': f'文件保存失败: {str(e)}'
        })

@login_required
def analyze_resume_api(request):
    """遗留接口：上传后已做文本与字段提取，此处不再生成完整报告。"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持POST请求'})
    
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '请先完善个人档案'})
    
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '无效的请求数据'})
    
    file_id = data.get('file_id')
    if not file_id:
        return JsonResponse({'success': False, 'message': '缺少文件ID'})
    
    import os
    from django.conf import settings
    file_path = os.path.join(settings.MEDIA_ROOT, file_id)
    if not os.path.exists(file_path):
        return JsonResponse({'success': False, 'message': '文件不存在'})
    
    return JsonResponse({
        'success': True,
        'message': '请继续确认简历信息，完整报告将在确认后生成',
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

def generate_ai_report(file, user):
    """生成AI报告（集成大模型API）"""
    from .ai_service import get_ai_service
    from .resume_parser import extract_text_from_resume
    import os
    from django.conf import settings
    
    # 获取文件路径
    if isinstance(file, str):
        # 如果file是文件路径字符串
        file_path = file
    elif hasattr(file, 'path'):
        # 如果file有path属性（Django FileField）
        file_path = file.path
    elif hasattr(file, 'read'):
        # 如果是文件对象，保存到临时位置
        import tempfile
        import uuid
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 获取原始文件名
        file_name = getattr(file, 'name', f'temp_{uuid.uuid4()}.pdf')
        file_path = os.path.join(temp_dir, os.path.basename(file_name))
        
        # 保存文件
        with open(file_path, 'wb') as f:
            if hasattr(file, 'chunks'):
                # Django上传文件
                for chunk in file.chunks():
                    f.write(chunk)
            else:
                # 普通文件对象
                f.write(file.read())
                file.seek(0)  # 重置文件指针
    else:
        raise ValueError(f"不支持的文件类型: {type(file)}")
    
    # 提取简历文本
    resume_text = extract_text_from_resume(file_path)
    
    if not resume_text:
        return """【AI职场竞争力报告】

⚠️ 无法提取简历文本内容
请确保上传的是有效的PDF或DOCX格式文件。
"""
    
    # 获取用户信息（可选）
    user_info = None
    try:
        profile = user.student_profile
        user_info = {
            'user_id': user.id,
            'email': user.email,
            'preferred_job_types': profile.get_preferred_job_types_list() if hasattr(profile, 'get_preferred_job_types_list') else [],
            # 添加用户确认的简历信息
            'confirmed_school': profile.ai_extracted_school or '',
            'confirmed_major': profile.ai_extracted_major or '',
            'confirmed_internship': profile.ai_extracted_internship_summary or '',
            'confirmed_hobbies': profile.ai_extracted_hobbies or '',
            'confirmed_skills': profile.ai_extracted_skills or [],
        }
    except:
        pass
    
    # 调用AI服务生成报告
    ai_service = get_ai_service()
    report = ai_service.analyze_resume(resume_text, user_info)
    
    # 清理临时文件
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    if 'temp' in file_path and os.path.dirname(file_path) == temp_dir:
        try:
            os.remove(file_path)
        except:
            pass
    
    return report

@login_required
def edit_resume_info(request):
    """简历信息编辑页面"""
    user = request.user
    
    # 获取学生档案
    try:
        profile = user.student_profile
    except StudentProfile.DoesNotExist:
        profile = None
    
    if not profile:
        messages.warning(request, '请先完善个人档案')
        return redirect('account_profile')
    
    # 如果没有简历，重定向到上传页面
    if not profile.resume:
        messages.info(request, '请先上传简历')
        return redirect('ai_plan')
    
    # 如果没有完成AI提取，尝试提取
    if not profile.ai_extraction_completed:
        from .resume_parser import extract_text_from_resume
        from .resume_extractor import extract_resume_info
        from django.conf import settings
        import os
        
        try:
            file_path = os.path.join(settings.MEDIA_ROOT, profile.resume.name)
            resume_text = extract_text_from_resume(file_path)
            if resume_text:
                extracted_info = extract_resume_info(resume_text)
                profile.ai_extracted_school = extracted_info.get('school', '')
                profile.ai_extracted_major = extracted_info.get('major', '')
                profile.ai_extracted_internship_summary = extracted_info.get('internship_summary', '')
                profile.ai_extracted_hobbies = extracted_info.get('hobbies', '')
                profile.ai_extracted_skills = extracted_info.get('skills', [])
                profile.ai_extraction_completed = True
                profile.ai_extraction_updated_at = timezone.now()
                profile.save()
        except Exception as e:
            logger.error(f"自动提取简历信息失败: {str(e)}")
    
    return render(request, 'jobs/edit_resume_info.html', {
        'profile': profile,
        'user': user,
    })

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
    parsed_report = None
    parsed_report_json = None
    
    if profile:
        ai_report = profile.ai_report
        report_updated_at = profile.ai_report_updated_at
        has_report = bool(ai_report and ai_report.strip())
        
        # 解析报告内容
        if has_report:
            from .report_parser import parse_ai_report
            import json
            parsed_report = parse_ai_report(ai_report)
            parsed_report_json = json.dumps(parsed_report, ensure_ascii=False)
    
    return render(request, 'jobs/ai_result.html', {
        'profile': profile,
        'user': user,
        'ai_report': ai_report,
        'report_updated_at': report_updated_at,
        'has_report': has_report,
        'parsed_report': parsed_report,
        'parsed_report_json': parsed_report_json,
    })

@login_required
def save_resume_info_api(request):
    """API: 保存简历信息（不触发完整分析）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持POST请求'})
    
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '请先完善个人档案'})
    
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '无效的请求数据'})
    
    # 更新字段
    if 'school' in data:
        profile.ai_extracted_school = data['school'].strip()
    if 'major' in data:
        profile.ai_extracted_major = data['major'].strip()
    if 'internship_summary' in data:
        profile.ai_extracted_internship_summary = data['internship_summary'].strip()
    if 'hobbies' in data:
        profile.ai_extracted_hobbies = data['hobbies'].strip()
    if 'skills' in data:
        # 确保skills是列表
        skills = data['skills']
        if isinstance(skills, list):
            profile.ai_extracted_skills = [s.strip() for s in skills if s.strip()]
        else:
            profile.ai_extracted_skills = []
    
    profile.save()
    
    return JsonResponse({
        'success': True,
        'message': '保存成功'
    })

@login_required
def confirm_resume_info_api(request):
    """API: 确认简历信息并触发完整AI分析"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持POST请求'})
    
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '请先完善个人档案'})
    
    if not profile.resume:
        return JsonResponse({'success': False, 'message': '请先上传简历'})
    
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '无效的请求数据'})
    
    # 更新字段
    if 'school' in data:
        profile.ai_extracted_school = data['school'].strip()
    if 'major' in data:
        profile.ai_extracted_major = data['major'].strip()
    if 'internship_summary' in data:
        profile.ai_extracted_internship_summary = data['internship_summary'].strip()
    if 'hobbies' in data:
        profile.ai_extracted_hobbies = data['hobbies'].strip()
    if 'skills' in data:
        skills = data['skills']
        if isinstance(skills, list):
            profile.ai_extracted_skills = [s.strip() for s in skills if s.strip()]
        else:
            profile.ai_extracted_skills = []
    
    profile.save()
    
    # 触发完整AI分析
    try:
        from .resume_parser import extract_text_from_resume
        from django.conf import settings
        import os
        
        file_path = os.path.join(settings.MEDIA_ROOT, profile.resume.name)
        resume_text = extract_text_from_resume(file_path)
        
        if resume_text:
            # 生成完整AI报告（会使用用户确认的信息）
            report = generate_ai_report(file_path, request.user)
            
            # 保存报告
            profile.ai_report = report
            profile.ai_report_updated_at = timezone.now()
            profile.save()
            
            return JsonResponse({
                'success': True,
                'message': '确认成功，AI分析已完成',
                'redirect_url': '/ai/result/'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '无法提取简历文本内容'
            })
    except Exception as e:
        logger.error(f"AI分析失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'AI分析失败: {str(e)}'
        })

def job_index_view(request):
    """职位列表页面视图（备选方案，如果 Wagtail 中没有 jobs 页面）"""
    from jobs.models import JobPage, JobIndexPage
    from django.db.models import Q
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    # 尝试从 Wagtail 获取 JobIndexPage
    job_index = JobIndexPage.objects.filter(slug='jobs').live().first()
    
    if job_index:
        # 如果 Wagtail 页面存在，使用 Wagtail 的页面服务机制
        # 这里重定向到 Wagtail 页面
        from django.shortcuts import redirect
        return redirect(job_index.url)
    
    # 如果 Wagtail 页面不存在，使用视图函数处理
    # 获取所有已发布的职位
    jobs = JobPage.objects.live().specific()
    
    # 1. 关键词搜索
    search_query = request.GET.get('q', '').strip()
    if search_query:
        jobs = jobs.filter(
            Q(job_title__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    # 2. 按职位类型筛选
    job_type = request.GET.get('job_type', '').strip()
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    
    # 3. 分页
    paginator = Paginator(jobs, 20)
    page = request.GET.get('page', 1)
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)
    
    # 为每个职位添加收藏状态
    if request.user.is_authenticated:
        for job in jobs:
            job.is_saved_by_user = job.is_saved_by_user(request.user)
    
    return render(request, 'jobs/job_index_page.html', {
        'job_pages': jobs,
        'search_query': search_query,
        'job_types': JobPage.JOB_TYPES,
    })

# Create your views here.
