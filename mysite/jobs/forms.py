from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import StudentProfile

# Import SignupForm - this will work once allauth is fully initialized
# The circular import is handled by django-allauth's lazy loading mechanism
from allauth.account.forms import SignupForm

User = get_user_model()

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
        
        # 将 username 字段设为隐藏，并设置为非必填
        # 这样 allauth 仍然会处理它，但我们会在 clean_username 中自动生成
        if 'username' in self.fields:
            self.fields['username'].required = False
            self.fields['username'].widget = forms.HiddenInput()
    
    def clean_email(self):
        """验证邮箱是否已存在"""
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(email=email).exists():
                raise ValidationError('该邮箱已被注册，请使用其他邮箱或直接登录。')
        return email
    
    def clean_username(self):
        """自动生成唯一的用户名（基于邮箱）"""
        # 如果表单中已经提供了 username，使用它（虽然通常是空的）
        username = self.cleaned_data.get('username', '')
        
        # 获取邮箱地址
        email = self.cleaned_data.get('email', '')
        
        # 如果没有邮箱，无法生成用户名
        if not email:
            # 如果已经有 username，使用它；否则返回一个临时值（会在 save 中处理）
            return username if username else 'temp_user'
        
        # 如果 username 为空或者是临时值，基于邮箱生成
        if not username or username == 'temp_user' or username.strip() == '':
            # 生成唯一的 username（基于邮箱）
            base_username = email.split('@')[0]  # 使用邮箱前缀
            # 清理用户名，只保留字母、数字和下划线
            import re
            base_username = re.sub(r'[^a-zA-Z0-9_]', '_', base_username)
            # 确保用户名不为空
            if not base_username:
                base_username = 'user'
            
            username = base_username
            counter = 1
            
            # 如果用户名已存在，添加数字后缀
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                # 防止无限循环
                if counter > 1000:
                    # 如果还是重复，使用邮箱本身加上时间戳
                    import time
                    username = f"{base_username}_{int(time.time())}"
                    break
        
        return username
    
    def save(self, request):
        # 确保 username 已经在 cleaned_data 中（通过 clean_username）
        email = self.cleaned_data.get('email', '')
        if not email:
            raise forms.ValidationError('邮箱地址不能为空')
        
        # 确保 username 已生成
        username = self.cleaned_data.get('username', '')
        if not username or username.strip() == '' or username == 'temp_user':
            username = self.clean_username()
            self.cleaned_data['username'] = username
        
        # 调用父类方法创建用户（username 已经在 clean_username 中自动生成）
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                user = super().save(request)
                break  # 成功，退出循环
            except Exception as e:
                retry_count += 1
                error_str = str(e).lower()
                
                # 检查是否是唯一性约束错误
                if 'unique constraint' in error_str or 'duplicate' in error_str or '1062' in error_str:
                    # 检查是否是邮箱重复
                    if email and User.objects.filter(email=email).exists():
                        raise forms.ValidationError('该邮箱已被注册，请使用其他邮箱或直接登录。')
                    
                    # 检查是否是用户名重复或空字符串
                    current_username = self.cleaned_data.get('username', '')
                    if (current_username and User.objects.filter(username=current_username).exists()) or \
                       (not current_username or current_username.strip() == ''):
                        # 重新生成用户名
                        if email:
                            username = self.clean_username()
                            self.cleaned_data['username'] = username
                            if retry_count < max_retries:
                                continue  # 重试
                            else:
                                raise forms.ValidationError('注册失败，用户名生成冲突，请稍后重试。')
                        else:
                            raise forms.ValidationError('注册失败，请稍后重试。')
                    else:
                        # 其他唯一性错误
                        raise forms.ValidationError('注册失败，请稍后重试。')
                else:
                    # 其他类型的错误，直接抛出
                    raise
        
        # 确保 username 被正确设置（双重保险）
        username = self.cleaned_data.get('username', '')
        if not user.username or user.username.strip() == '':
            if username and username != 'temp_user':
                user.username = username
            else:
                # 如果还是没有，使用邮箱生成
                email = self.cleaned_data.get('email', '')
                if email:
                    user.username = self.clean_username()
            user.save()
        
        # 确保 email 被正确设置
        email = self.cleaned_data.get('email', '')
        if email and (not user.email or user.email != email):
            user.email = email
            user.save()
        
        # 设置用户全名
        user.first_name = self.cleaned_data['full_name']
        user.save()
        
        # 获取或创建学生档案
        profile, created = StudentProfile.objects.get_or_create(user=user)
        
        # 更新学生档案信息
        profile.school = self.cleaned_data['school']
        profile.major = self.cleaned_data['major']
        profile.graduation_year = self.cleaned_data['graduation_year']
        profile.phone = self.cleaned_data.get('phone', '')
        
        # 处理多选的职位类型
        job_types = self.cleaned_data.get('preferred_job_types', [])
        profile.preferred_job_types = ','.join(job_types) if job_types else 'intern,fulltime'
        
        profile.preferred_locations = self.cleaned_data.get('preferred_locations', '北京,上海,深圳')
        profile.save()
        
        return user


class ProfileEditForm(forms.ModelForm):
    """编辑个人档案表单"""
    full_name = forms.CharField(
        max_length=100,
        label='真实姓名',
        widget=forms.TextInput(attrs={'placeholder': '请输入真实姓名', 'class': 'form-control'})
    )
    
    email = forms.EmailField(
        label='邮箱地址',
        widget=forms.EmailInput(attrs={'placeholder': '请输入常用邮箱', 'class': 'form-control'})
    )
    
    preferred_job_types = forms.MultipleChoiceField(
        choices=[
            ('intern', '实习'),
            ('fulltime', '全职'),
            ('parttime', '兼职'),
        ],
        label='求职类型',
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = StudentProfile
        fields = ['avatar', 'school', 'major', 'graduation_year', 'preferred_locations']
        widgets = {
            'school': forms.Select(attrs={'class': 'form-select'}),
            'major': forms.Select(attrs={'class': 'form-select'}),
            'graduation_year': forms.Select(attrs={'class': 'form-select'}),
            'preferred_locations': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如：北京,上海,深圳'
            }),
        }
        labels = {
            'school': '所在学校',
            'major': '所学专业',
            'graduation_year': '毕业年份',
            'preferred_locations': '期望工作城市',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 确保用户信息始终预填充（无论 profile 是否存在）
        # 只在首次加载时设置（没有提交数据时）
        if self.user and not self.data:
            # 基本信息：从用户对象获取
            self.fields['full_name'].initial = self.user.get_full_name() or self.user.first_name or ''
            self.fields['email'].initial = self.user.email or ''
            
            # 学生信息：从 profile 实例获取，如果不存在则使用默认值
            # ModelForm 会自动从 instance 填充数据，但如果 instance 不存在或字段为空，需要设置默认值
            if self.instance and self.instance.pk:
                # Profile 已存在，ModelForm 会自动填充，但确保空字段有默认值
                # 对于 preferred_job_types，需要特殊处理（从字符串转换为列表）
                if hasattr(self.instance, 'get_preferred_job_types_list'):
                    self.fields['preferred_job_types'].initial = self.instance.get_preferred_job_types_list()
                # 其他字段 ModelForm 会自动填充，但如果为空则设置默认值
                if not self.instance.school:
                    self.fields['school'].initial = 'other'
                if not self.instance.major:
                    self.fields['major'].initial = 'other'
                if not self.instance.graduation_year:
                    self.fields['graduation_year'].initial = 2025
                if not self.instance.preferred_locations:
                    self.fields['preferred_locations'].initial = '北京,上海,深圳'
            else:
                # Profile 不存在，使用默认值
                self.fields['school'].initial = 'other'
                self.fields['major'].initial = 'other'
                self.fields['graduation_year'].initial = 2025
                self.fields['preferred_locations'].initial = '北京,上海,深圳'
                self.fields['preferred_job_types'].initial = ['intern', 'fulltime']
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # 更新用户信息
        if self.user:
            self.user.email = self.cleaned_data['email']
            self.user.first_name = self.cleaned_data['full_name']
            self.user.save()
        
        # 处理多选的职位类型
        job_types = self.cleaned_data.get('preferred_job_types', [])
        profile.preferred_job_types = ','.join(job_types) if job_types else 'intern,fulltime'
        
        if commit:
            profile.save()
        
        return profile