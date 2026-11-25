from django.db import migrations, models
import django.db.models.deletion


DOCUMENT_COLUMNS = [
    'Passport',
    'PS Form',
    'Predicted Grades',
    'Transcripts',
    'Statement',
    'Recommendation Letters',
    'English Exam',
    'Picture',
]


def seed_document_tracker(apps, schema_editor):
    PlatformUser = apps.get_model('portal', 'PlatformUser')
    DocumentTrackerColumn = apps.get_model('portal', 'DocumentTrackerColumn')
    DocumentTrackerRow = apps.get_model('portal', 'DocumentTrackerRow')
    DocumentTrackerCell = apps.get_model('portal', 'DocumentTrackerCell')

    columns = []
    for index, name in enumerate(DOCUMENT_COLUMNS):
        columns.append(DocumentTrackerColumn.objects.create(name=name, sort_order=index))

    existing_student_ids = set(DocumentTrackerRow.objects.values_list('student_id', flat=True))
    students = PlatformUser.objects.filter(role='student').order_by('id')
    sort_order = 0

    for student in students:
        if student.id in existing_student_ids:
            row = DocumentTrackerRow.objects.get(student_id=student.id)
        else:
            row = DocumentTrackerRow.objects.create(student_id=student.id, sort_order=sort_order)
            sort_order += 1

        for column in columns:
            DocumentTrackerCell.objects.get_or_create(
                row_id=row.id,
                column_id=column.id,
                defaults={'status': 'not_sent'},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0053_notion_task_tracker_statuses'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentTrackerColumn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Document tracker column',
                'verbose_name_plural': 'Document tracker columns',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='DocumentTrackerRow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assignee', models.CharField(blank=True, default='', max_length=200)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.OneToOneField(
                    limit_choices_to={'role': 'student'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='document_tracker_row',
                    to='portal.platformuser',
                )),
            ],
            options={
                'verbose_name': 'Document tracker row',
                'verbose_name_plural': 'Document tracker rows',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='DocumentTrackerCell',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('done', 'Done'),
                        ('in_progress', 'In progress'),
                        ('not_sent', 'Not sent'),
                        ('not_applicable', 'Not applicable'),
                    ],
                    default='not_sent',
                    max_length=20,
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('column', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cells',
                    to='portal.documenttrackercolumn',
                )),
                ('row', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cells',
                    to='portal.documenttrackerrow',
                )),
            ],
            options={
                'verbose_name': 'Document tracker cell',
                'verbose_name_plural': 'Document tracker cells',
            },
        ),
        migrations.AddConstraint(
            model_name='documenttrackercell',
            constraint=models.UniqueConstraint(fields=('row', 'column'), name='unique_document_tracker_cell'),
        ),
        migrations.RunPython(seed_document_tracker, migrations.RunPython.noop),
    ]