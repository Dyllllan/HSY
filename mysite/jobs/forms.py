from django import forms
from .models import StudentProfile

# Import SignupForm - this will work once allauth is fully initialized
# The circular import is handled by django-allauth's lazy loading mechanism
from allauth.account.forms import SignupForm

class CustomSignupForm(SignupForm):
    """自定义注册表单，收集学生信息"""
    # 基础信息
    full_name = forms.CharField(
        max_length=100,
        label='真实姓名',
        widget=forms.TextInput(attrs={'placeholder': '请输入真实姓名'})
    )
    
    # 学生信息
    school = forms.ChoiceField(
        choices=StudentProfile.SCHOOL_CHOICES,
        label='所在学校',
        initial='other'
    )
    
    major = forms.ChoiceField(
        choices=StudentProfile.MAJOR_CHOICES,
        label='所学专业',
        initial='other'
    )
    
    graduation_year = forms.ChoiceField(
        choices=[(year, str(year)) for year in range(2024, 2030)],
        label='毕业年份',
        initial=2025
    )
    
    # 求职偏好
    preferred_job_types = forms.MultipleChoiceField(
        choices=[
            ('intern', '实习'),
            ('fulltime', '全职'),
            ('parttime', '兼职'),
        ],
        label='求职类型',
        initial=['intern', 'fulltime'],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    preferred_locations = forms.CharField(
        max_length=200,
        label='期望工作城市',
        initial='北京,上海,深圳',
        help_text='多个城市用逗号分隔',
        widget=forms.TextInput(attrs={'placeholder': '例如：北京,上海,深圳'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 调整字段顺序
        self.fields['email'].widget.attrs.update({'placeholder': '请输入常用邮箱'})
        self.fields['password1'].widget.attrs.update({'placeholder': '设置登录密码'})
        
        # 移除默认的用户名字段
        if 'username' in self.fields:
            del self.fields['username']
    
    def save(self, request):
        # 调用父类方法创建用户
        user = super().save(request)
        
        # 设置用户全名
        user.first_name = self.cleaned_data['full_name']
        user.save()
        
        # 获取或创建学生档案
        profile, created = StudentProfile.objects.get_or_create(user=user)
        
        # 更新学生档案信息
        profile.school = self.cleaned_data['school']
        profile.major = self.cleaned_data['major']
        profile.graduation_year = self.cleaned_data['graduation_year']
        
        # 处理多选的职位类型
        job_types = self.cleaned_data.get('preferred_job_types', [])
        profile.preferred_job_types = ','.join(job_types) if job_types else 'intern,fulltime'
        
        profile.preferred_locations = self.cleaned_data.get('preferred_locations', '北京,上海,深圳')
        profile.save()
        
        return user
    """自定义注册表单，收集学生信息"""
    # 基础信息
    full_name = forms.CharField(
        max_length=100,
        label='真实姓名',
        widget=forms.TextInput(attrs={'placeholder': '请输入真实姓名'})
    )
    
    # 学生信息
    school = forms.ChoiceField(
        choices=StudentProfile.SCHOOL_CHOICES,
        label='所在学校',
        initial='other'
    )
    
    major = forms.ChoiceField(
        choices=StudentProfile.MAJOR_CHOICES,
        label='所学专业',
        initial='other'
    )
    
    graduation_year = forms.ChoiceField(
        choices=[(year, str(year)) for year in range(2024, 2030)],
        label='毕业年份',
        initial=2025
    )
    
    # 求职偏好
    preferred_job_types = forms.MultipleChoiceField(
        choices=[
            ('intern', '实习'),
            ('fulltime', '全职'),
            ('parttime', '兼职'),
        ],
        label='求职类型',
        initial=['intern', 'fulltime'],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    preferred_locations = forms.CharField(
        max_length=200,
        label='期望工作城市',
        initial='北京,上海,深圳',
        help_text='多个城市用逗号分隔',
        widget=forms.TextInput(attrs={'placeholder': '例如：北京,上海,深圳'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 调整字段顺序
        self.fields['email'].widget.attrs.update({'placeholder': '请输入常用邮箱'})
        self.fields['password1'].widget.attrs.update({'placeholder': '设置登录密码'})
        
        # 移除默认的用户名字段
        if 'username' in self.fields:
            del self.fields['username']
    
    def save(self, request):
        # 调用父类方法创建用户
        user = super().save(request)
        
        # 设置用户全名
        user.first_name = self.cleaned_data['full_name']
        user.save()
        
        # 获取或创建学生档案
        profile, created = StudentProfile.objects.get_or_create(user=user)
        
        # 更新学生档案信息
        profile.school = self.cleaned_data['school']
        profile.major = self.cleaned_data['major']
        profile.graduation_year = self.cleaned_data['graduation_year']
        
        # 处理多选的职位类型
        job_types = self.cleaned_data.get('preferred_job_types', [])
        profile.preferred_job_types = ','.join(job_types) if job_types else 'intern,fulltime'
        
        profile.preferred_locations = self.cleaned_data.get('preferred_locations', '北京,上海,深圳')
        profile.save()
        
        return user