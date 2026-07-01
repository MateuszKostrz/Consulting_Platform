from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0019_academicactivityentry'),
    ]

    operations = [
        migrations.AddField(
            model_name='academicprofile',
            name='excluded_countries_cities',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='academicprofile',
            name='primary_course_preference',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='academicprofile',
            name='secondary_course_preference',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
