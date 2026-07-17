from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0023_personalprofile_parent_guardian_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='personalprofile',
            name='curriculum_other',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
