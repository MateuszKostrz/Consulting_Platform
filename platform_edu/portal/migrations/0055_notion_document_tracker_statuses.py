from django.db import migrations


def apply_notion_document_statuses(apps, schema_editor):
    from portal.notion_document_tracker_seed import NOTION_DOCUMENT_TRACKER_BY_USER_ID

    DocumentTrackerRow = apps.get_model('portal', 'DocumentTrackerRow')
    DocumentTrackerColumn = apps.get_model('portal', 'DocumentTrackerColumn')
    DocumentTrackerCell = apps.get_model('portal', 'DocumentTrackerCell')

    columns = list(DocumentTrackerColumn.objects.order_by('sort_order', 'id')[:8])
    if len(columns) != 8:
        return

    for student_id, statuses in NOTION_DOCUMENT_TRACKER_BY_USER_ID.items():
        if len(statuses) != len(columns):
            continue
        row = DocumentTrackerRow.objects.filter(student_id=student_id).first()
        if not row:
            continue
        for column, status in zip(columns, statuses):
            DocumentTrackerCell.objects.update_or_create(
                row_id=row.id,
                column_id=column.id,
                defaults={'status': status},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0054_document_tracker'),
    ]

    operations = [
        migrations.RunPython(apply_notion_document_statuses, migrations.RunPython.noop),
    ]