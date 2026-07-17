from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0027_strategicapplication_choices_approved_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='profilenarrative',
            name='application_essays_google_doc_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='profilenarrative',
            name='cv_google_doc_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='profilenarrative',
            name='personal_statement_google_doc_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
    ]
