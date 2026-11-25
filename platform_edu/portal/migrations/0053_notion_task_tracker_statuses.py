from django.db import migrations


def apply_notion_statuses(apps, schema_editor):
    from portal.notion_task_tracker_seed import NOTION_TASK_TRACKER_BY_USER_ID

    TaskTrackerRow = apps.get_model('portal', 'TaskTrackerRow')
    TaskTrackerColumn = apps.get_model('portal', 'TaskTrackerColumn')
    TaskTrackerCell = apps.get_model('portal', 'TaskTrackerCell')

    columns = list(TaskTrackerColumn.objects.order_by('sort_order', 'id'))
    if len(columns) != 11:
        return

    for student_id, statuses in NOTION_TASK_TRACKER_BY_USER_ID.items():
        if len(statuses) != len(columns):
            continue
        row = TaskTrackerRow.objects.filter(student_id=student_id).first()
        if not row:
            continue
        for column, status in zip(columns, statuses):
            TaskTrackerCell.objects.update_or_create(
                row_id=row.id,
                column_id=column.id,
                defaults={'status': status},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0052_task_tracker_column_names'),
    ]

    operations = [
        migrations.RunPython(apply_notion_statuses, migrations.RunPython.noop),
    ]