from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0045_rename_client_comments_student_comments'),
    ]

    operations = [
        migrations.AddField(
            model_name='academicprofile',
            name='personal_statement_assessment',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]