from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0034_alter_resultdocument_document_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfoliodesign',
            name='checklist_approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
