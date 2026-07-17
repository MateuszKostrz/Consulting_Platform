from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0022_platformuser_visible_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='personalprofile',
            name='parent_first_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='personalprofile',
            name='parent_last_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='personalprofile',
            name='parent_phone',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]
