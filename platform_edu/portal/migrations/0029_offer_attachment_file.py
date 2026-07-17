from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0028_profilenarrative_google_doc_urls'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='attachment_file',
            field=models.FileField(blank=True, null=True, upload_to='offers/attachments/'),
        ),
    ]
