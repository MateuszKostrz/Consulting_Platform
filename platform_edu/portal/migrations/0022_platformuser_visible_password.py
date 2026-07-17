from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0021_academicprofile_budget_currency'),
    ]

    operations = [
        migrations.AddField(
            model_name='platformuser',
            name='visible_password',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Last known password, stored for admin reference when the account is created.',
                max_length=128,
            ),
        ),
    ]
