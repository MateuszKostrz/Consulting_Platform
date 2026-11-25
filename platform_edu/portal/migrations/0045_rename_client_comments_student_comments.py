from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0044_portfoliodesign_client_comments'),
    ]

    operations = [
        migrations.RenameField(
            model_name='portfoliodesign',
            old_name='client_comments',
            new_name='student_comments',
        ),
    ]