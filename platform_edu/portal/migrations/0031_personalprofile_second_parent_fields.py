from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0030_results_resultdocument'),
    ]

    operations = [
        migrations.AddField(
            model_name='personalprofile',
            name='parent2_first_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='personalprofile',
            name='parent2_last_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='personalprofile',
            name='parent2_email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AddField(
            model_name='personalprofile',
            name='parent2_phone',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]
