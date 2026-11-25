from django.db import migrations


def sync_students(apps, schema_editor):
    PlatformUser = apps.get_model('portal', 'PlatformUser')
    TaskTrackerColumn = apps.get_model('portal', 'TaskTrackerColumn')
    TaskTrackerRow = apps.get_model('portal', 'TaskTrackerRow')
    TaskTrackerCell = apps.get_model('portal', 'TaskTrackerCell')

    columns = list(TaskTrackerColumn.objects.order_by('sort_order', 'id'))
    if not columns:
        return

    existing_student_ids = set(TaskTrackerRow.objects.values_list('student_id', flat=True))
    students = PlatformUser.objects.filter(role='student').order_by('id')
    sort_order = TaskTrackerRow.objects.count()

    for student in students:
        if student.id in existing_student_ids:
            row = TaskTrackerRow.objects.get(student_id=student.id)
        else:
            row = TaskTrackerRow.objects.create(
                student_id=student.id,
                sort_order=sort_order,
            )
            sort_order += 1
            existing_student_ids.add(student.id)

        for column in columns:
            TaskTrackerCell.objects.get_or_create(
                row_id=row.id,
                column_id=column.id,
                defaults={'status': 'not_started'},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0050_task_tracker'),
    ]

    operations = [
        migrations.RunPython(sync_students, migrations.RunPython.noop),
    ]