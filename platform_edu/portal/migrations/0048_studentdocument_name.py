from django.db import migrations, models
import os


def backfill_document_names(apps, schema_editor):
    StudentDocument = apps.get_model('portal', 'StudentDocument')
    for document in StudentDocument.objects.all().iterator():
        if document.name or not document.document_file:
            continue
        document.name = os.path.basename(document.document_file.name)
        document.save(update_fields=['name'])


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0047_studentsectionaccess_self_assessment'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentdocument',
            name='name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.RunPython(backfill_document_names, migrations.RunPython.noop),
    ]