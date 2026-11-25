from django.db import migrations, models


def forwards_copy_legacy_urls(apps, schema_editor):
    ProfileNarrative = apps.get_model('portal', 'ProfileNarrative')
    mapping = (
        ('personal_statement', 'personal_statement_google_doc_url', 'Personal Statement'),
        ('cv', 'cv_google_doc_url', 'CV'),
        ('application_essays', 'application_essays_google_doc_url', 'Application Essays'),
    )
    for narrative in ProfileNarrative.objects.iterator():
        payload = dict(narrative.document_links or {})
        changed = False
        for section_key, url_field, default_title in mapping:
            if payload.get(section_key):
                continue
            url = (getattr(narrative, url_field) or '').strip()
            if url:
                payload[section_key] = [{'title': default_title, 'url': url}]
                changed = True
        if changed:
            narrative.document_links = payload
            narrative.save(update_fields=['document_links'])


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0042_whatsapp_donna_webhook'),
    ]

    operations = [
        migrations.AddField(
            model_name='profilenarrative',
            name='document_links',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(forwards_copy_legacy_urls, migrations.RunPython.noop),
    ]