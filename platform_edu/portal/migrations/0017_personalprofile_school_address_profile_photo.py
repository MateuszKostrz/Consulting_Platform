from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0016_studenttodo'),
    ]

    operations = [
        migrations.AddField(
            model_name='personalprofile',
            name='school_address',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='personalprofile',
            name='profile_photo',
            field=models.ImageField(blank=True, null=True, upload_to='personal/profile_photos/'),
        ),
    ]
