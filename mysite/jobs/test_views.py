"""
测试视图：用于诊断 django-allauth 问题
"""
from django.shortcuts import render
from django.http import HttpResponse

def test_signup_view(request):
    """测试 signup 视图是否能正常工作"""
    return render(request, 'account/signup.html', {
        'form': None,  # 临时测试，不传递表单
    })
