from django.db import migrations, models
import django.db.models.deletion


DEFAULT_COLUMNS = [
    'Onboarding',
    'Forms Sent',
    'Diagnostic',
    'Achievement',
    'Research',
    'Choices',
]


def seed_task_tracker_columns(apps, schema_editor):
    TaskTrackerColumn = apps.get_model('portal', 'TaskTrackerColumn')
    if TaskTrackerColumn.objects.exists():
        return
    for index, name in enumerate(DEFAULT_COLUMNS):
        TaskTrackerColumn.objects.create(name=name, sort_order=index)


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0049_deadline_student_nullable'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskTrackerColumn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Task tracker column',
                'verbose_name_plural': 'Task tracker columns',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='TaskTrackerRow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assignee', models.CharField(blank=True, default='', max_length=200)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.OneToOneField(
                    limit_choices_to={'role': 'student'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='task_tracker_row',
                    to='portal.platformuser',
                )),
            ],
            options={
                'verbose_name': 'Task tracker row',
                'verbose_name_plural': 'Task tracker rows',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='TaskTrackerCell',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('done', 'Done'),
                        ('in_progress', 'In progress'),
                        ('not_started', 'Not started'),
                        ('not_applicable', 'Not applicable'),
                    ],
                    default='not_started',
                    max_length=20,
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('column', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cells',
                    to='portal.tasktrackercolumn',
                )),
                ('row', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cells',
                    to='portal.tasktrackerrow',
                )),
            ],
            options={
                'verbose_name': 'Task tracker cell',
                'verbose_name_plural': 'Task tracker cells',
            },
        ),
        migrations.AddConstraint(
            model_name='tasktrackercell',
            constraint=models.UniqueConstraint(fields=('row', 'column'), name='unique_task_tracker_cell'),
        ),
        migrations.RunPython(seed_task_tracker_columns, migrations.RunPython.noop),
    ]