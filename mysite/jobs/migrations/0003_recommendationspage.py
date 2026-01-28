# Generated manually for RecommendationsPage model

import wagtail.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0096_referenceindex_referenceindex_source_object_and_more'),
        ('jobs', '0002_jobapplication'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecommendationsPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('intro', wagtail.fields.RichTextField(blank=True, help_text='显示在推荐列表上方的介绍文字', verbose_name='页面介绍')),
            ],
            options={
                'verbose_name': '个性化推荐页面',
                'verbose_name_plural': '个性化推荐页面',
            },
            bases=('wagtailcore.page',),
        ),
    ]
