from django.db import migrations

NEW_COLUMNS = [
    'Onboarding',
    'Forms Sent',
    'Diagnostic',
    'Achievements',
    'Research',
    'Choices Made',
    'PS',
    'Email Created',
    'CV',
    'Docs',
    'Application Portals',
]


def sync_columns(apps, schema_editor):
    TaskTrackerColumn = apps.get_model('portal', 'TaskTrackerColumn')
    TaskTrackerRow = apps.get_model('portal', 'TaskTrackerRow')
    TaskTrackerCell = apps.get_model('portal', 'TaskTrackerCell')

    existing = list(TaskTrackerColumn.objects.order_by('sort_order', 'id'))
    for index, name in enumerate(NEW_COLUMNS):
        if index < len(existing):
            column = existing[index]
            column.name = name
            column.sort_order = index
            column.save(update_fields=['name', 'sort_order'])
        else:
            TaskTrackerColumn.objects.create(name=name, sort_order=index)

    if len(existing) > len(NEW_COLUMNS):
        for column in existing[len(NEW_COLUMNS) :]:
            TaskTrackerCell.objects.filter(column_id=column.id).delete()
            column.delete()

    for row in TaskTrackerRow.objects.all():
        for column in TaskTrackerColumn.objects.all():
            TaskTrackerCell.objects.get_or_create(
                row_id=row.id,
                column_id=column.id,
                defaults={'status': 'not_started'},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0051_sync_task_tracker_students'),
    ]

    operations = [
        migrations.RunPython(sync_columns, migrations.RunPython.noop),
    ]