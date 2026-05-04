from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.timezone import now as timezone_now
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
from .models import JobPage, JobApplication

@csrf_exempt
@require_POST
def toggle_save_job(request):
    """收藏/取消收藏职位（与投递状态互不覆盖）"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        if not request.user.is_authenticated:
            logger.warning('Unauthenticated user attempted to save job')
            return JsonResponse({'error': '请先登录', 'login_required': True}, status=401)
        
        try:
            data = json.loads(request.body)
            logger.info(f'Received save job request from user {request.user.id}: {data}')
        except json.JSONDecodeError:
            logger.error(f'Invalid JSON in request body: {request.body}')
            return JsonResponse({'error': '无效的请求数据'}, status=400)
        
        job_id = data.get('job_id')
        
        if not job_id:
            logger.error('Missing job_id in request')
            return JsonResponse({'error': '缺少职位ID'}, status=400)
        
        try:
            job_page = JobPage.objects.get(id=job_id)
        except JobPage.DoesNotExist:
            logger.error(f'JobPage with id {job_id} does not exist')
            return JsonResponse({'error': '职位不存在'}, status=404)
        except ValueError as e:
            logger.error(f'Invalid job_id format: {job_id}, error: {e}')
            return JsonResponse({'error': '无效的职位ID'}, status=400)
        
        existing = JobApplication.objects.filter(
            user=request.user,
            job_page=job_page,
        ).first()
        
        if existing:
            if existing.is_saved:
                existing.is_saved = False
                if existing.applied_at is None:
                    existing.delete()
                    action = 'unsaved'
                else:
                    existing.save(update_fields=['is_saved', 'updated_at'])
                    action = 'unsaved'
                logger.info(f'User {request.user.id} unsaved job {job_id}')
            else:
                existing.is_saved = True
                existing.save(update_fields=['is_saved', 'updated_at'])
                action = 'saved'
                logger.info(f'User {request.user.id} saved job {job_id}')
        else:
            JobApplication.objects.create(
                user=request.user,
                job_page=job_page,
                is_saved=True,
                status='',
                applied_at=None,
                ip_address=get_client_ip(request),
            )
            action = 'saved'
            logger.info(f'User {request.user.id} saved job {job_id}')
        
        job_page.refresh_from_db()
        return JsonResponse({
            'success': True,
            'action': action,
            'save_count': job_page.save_count,
            'is_saved': action == 'saved'
        })
        
    except Exception as e:
        logger.exception(f'Unexpected error in toggle_save_job: {e}')
        return JsonResponse({
            'error': '服务器内部错误',
            'detail': str(e) if settings.DEBUG else None
        }, status=500)

@require_POST
def apply_job(request):
    """记录投递后再由前端打开外部投递链接"""
    if not request.user.is_authenticated:
        return JsonResponse(
            {'success': False, 'error': '请先登录', 'login_required': True},
            status=401,
        )
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的请求数据'}, status=400)
    
    job_id = data.get('job_id')
    if not job_id:
        return JsonResponse({'success': False, 'error': '缺少职位ID'}, status=400)
    
    try:
        job_page = JobPage.objects.get(id=job_id)
    except JobPage.DoesNotExist:
        return JsonResponse({'success': False, 'error': '职位不存在'}, status=404)
    
    application, created = JobApplication.objects.get_or_create(
        user=request.user,
        job_page=job_page,
        defaults={
            'is_saved': False,
            'applied_at': timezone_now(),
            'status': 'applied',
            'ip_address': get_client_ip(request),
        },
    )
    if not created:
        if application.applied_at is None:
            application.applied_at = timezone_now()
        if not application.status:
            application.status = 'applied'
        application.ip_address = get_client_ip(request)
        application.save(update_fields=['applied_at', 'status', 'ip_address', 'updated_at'])
    
    log_application_event(request.user, job_page, 'applied')
    
    return JsonResponse({
        'success': True,
        'job_title': job_page.job_title,
        'company': job_page.company_name,
        'external_url': job_page.source_url or '',
        'applied_at': application.applied_at.isoformat() if application.applied_at else None,
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
    pass


@login_required
@require_http_methods(['POST'])
def update_application_notes(request, application_id):
    """更新投递备注（工作台）"""
    try:
        application = JobApplication.objects.get(pk=application_id, user=request.user)
    except JobApplication.DoesNotExist:
        return JsonResponse({'success': False, 'message': '记录不存在'}, status=404)
    
    try:
        data = json.loads(request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '无效的 JSON'}, status=400)
    
    application.notes = (data.get('notes') or '')[:4000]
    application.save(update_fields=['notes', 'updated_at'])
    return JsonResponse({'success': True, 'notes': application.notes})


@csrf_exempt
@require_POST
def track_recommendation_click(request):
    """推荐位点击打点（无副作用，不要求登录也可调用）"""
    try:
        data = json.loads(request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False}, status=400)
    
    job_id = data.get('job_id')
    if job_id:
        log_application_event(
            getattr(request, 'user', None),
            None,
            f"recommendation_click:{data.get('recommendation_type', 'unknown')}:{job_id}",
        )
    return JsonResponse({'success': True})
