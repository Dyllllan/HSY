# Generated manually for separating save vs apply semantics

from django.db import migrations, models


def forwards_migrate_saved_status(apps, schema_editor):
    JobApplication = apps.get_model("jobs", "JobApplication")
    for app in JobApplication.objects.all():
        raw = getattr(app, "status", "") or ""
        if raw == "saved":
            app.is_saved = True
            app.status = ""
            app.applied_at = None
            app.save(update_fields=["is_saved", "status", "applied_at"])
        elif raw == "viewed":
            app.status = ""
            app.save(update_fields=["status"])
        # applied / contacted / rejected / accepted: unchanged status; applied keeps applied_at


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0008_resumeindexpage_resumepage"),
    ]

    operations = [
        migrations.RenameField(
            model_name="jobapplication",
            old_name="applied_date",
            new_name="applied_at",
        ),
        migrations.AddField(
            model_name="jobapplication",
            name="is_saved",
            field=models.BooleanField(default=False, verbose_name="是否收藏"),
        ),
        migrations.RunPython(forwards_migrate_saved_status, noop_reverse),
        migrations.AlterField(
            model_name="jobapplication",
            name="status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("applied", "已投递"),
                    ("contacted", "已联系"),
                    ("rejected", "已拒绝"),
                    ("accepted", "已接受"),
                ],
                default="",
                max_length=20,
                verbose_name="投递进度",
            ),
        ),
    ]
