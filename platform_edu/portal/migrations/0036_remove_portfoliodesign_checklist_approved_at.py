from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0035_portfoliodesign_checklist_approved_at'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='portfoliodesign',
            name='checklist_approved_at',
        ),
    ]
