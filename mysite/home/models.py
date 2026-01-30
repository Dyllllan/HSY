from django.db import models

from wagtail.models import Page


class HomePage(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # 获取职位数据
        from jobs.models import JobPage, JobIndexPage
        
        # 查找 JobIndexPage
        job_index = JobIndexPage.objects.live().first()
        if job_index:
            # 获取热门职位（限制10条）
            jobs = JobPage.objects.child_of(job_index).live().specific()[:10]
            # 为每个职位添加收藏状态（如果用户已登录）
            if request.user.is_authenticated:
                for job in jobs:
                    job.is_saved_by_user = job.is_saved_by_user(request.user)
            context['jobs'] = jobs
        else:
            context['jobs'] = []
        
        return context
