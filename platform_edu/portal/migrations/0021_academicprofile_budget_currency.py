from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0020_academicprofile_course_wishes'),
    ]

    operations = [
        migrations.AddField(
            model_name='academicprofile',
            name='budget_currency',
            field=models.CharField(blank=True, default='USD', max_length=3),
        ),
    ]
