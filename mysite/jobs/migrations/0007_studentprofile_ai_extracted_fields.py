# Generated manually

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0006_studentprofile_ai_report_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='ai_extracted_school',
            field=models.CharField(blank=True, help_text='AI从简历中提取的学校名称', max_length=200, verbose_name='AI提取的学校'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='ai_extracted_major',
            field=models.CharField(blank=True, help_text='AI从简历中提取的专业名称', max_length=200, verbose_name='AI提取的专业'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='ai_extracted_internship_summary',
            field=models.TextField(blank=True, help_text='AI从简历中总结的实习经历', verbose_name='AI提取的实习经历总结'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='ai_extracted_hobbies',
            field=models.TextField(blank=True, help_text='AI从简历中提取的爱好和职业兴趣', verbose_name='AI提取的爱好/职业兴趣'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='ai_extracted_skills',
            field=models.JSONField(blank=True, default=list, help_text='AI从简历中提取的核心技能列表', verbose_name='AI提取的核心技能'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='ai_extraction_completed',
            field=models.BooleanField(default=False, help_text='AI是否已完成初步信息提取', verbose_name='AI初步提取完成'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='ai_extraction_updated_at',
            field=models.DateTimeField(blank=True, help_text='AI初步信息提取的最后更新时间', null=True, verbose_name='AI提取更新时间'),
        ),
    ]
