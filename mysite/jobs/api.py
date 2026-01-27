from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now as timezone_now
import json
from .models import JobPage, JobApplication

@csrf_exempt
@require_POST
@login_required
def toggle_save_job(request):
    """收藏/取消收藏职位"""
    data = json.loads(request.body)
    job_id = data.get('job_id')
    
    try:
        job_page = JobPage.objects.get(id=job_id)
    except JobPage.DoesNotExist:
        return JsonResponse({'error': '职位不存在'}, status=404)
    
    # 检查是否已收藏
    existing = JobApplication.objects.filter(
        user=request.user,
        job_page=job_page,
        status='saved'
    ).first()
    
    if existing:
        # 取消收藏
        existing.delete()
        action = 'unsaved'
    else:
        # 添加收藏
        JobApplication.objects.create(
            user=request.user,
            job_page=job_page,
            status='saved',
            ip_address=get_client_ip(request)
        )
        action = 'saved'
    
    return JsonResponse({
        'action': action,
        'save_count': job_page.save_count,
        'is_saved': action == 'saved'
    })

@csrf_exempt
@require_POST
@login_required
def apply_job(request):
    """申请职位（跳转到外部链接）"""
    data = json.loads(request.body)
    job_id = data.get('job_id')
    
    try:
        job_page = JobPage.objects.get(id=job_id)
    except JobPage.DoesNotExist:
        return JsonResponse({'error': '职位不存在'}, status=404)
    
    # 创建或更新申请记录
    application, created = JobApplication.objects.update_or_create(
        user=request.user,
        job_page=job_page,
        defaults={
            'status': 'applied',
            'ip_address': get_client_ip(request),
            'applied_date': timezone_now()
        }
    )
    
    # 记录申请事件（可用于后续分析）
    log_application_event(request.user, job_page, 'applied')
    
    return JsonResponse({
        'success': True,
        'job_title': job_page.job_title,
        'company': job_page.company_name,
        'external_url': job_page.source_url,
        'applied_at': application.applied_date.isoformat()
    })

def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_application_event(user, job_page, event_type):
    """记录申请事件（可用于分析）"""
    # 这里可以集成到分析系统，如Google Analytics或自建事件追踪
    pass