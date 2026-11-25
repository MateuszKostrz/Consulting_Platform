from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0043_profilenarrative_document_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfoliodesign',
            name='client_comments',
            field=models.TextField(blank=True, default=''),
        ),
    ]