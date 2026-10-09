from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0040_universitychoice_comments_preview_rows'),
    ]

    operations = [
        migrations.AddField(
            model_name='universitychoice',
            name='due_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='universitychoice',
            name='due_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='universitychoice',
            name='due_timezone',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]
