from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0006_diagnosticstage'),
    ]

    operations = [
        migrations.CreateModel(
            name='Deadline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('due_at', models.DateTimeField()),
                ('urgency', models.CharField(
                    choices=[('urgent', 'Urgent'), ('standard', 'Standard'), ('relaxed', 'Relaxed')],
                    default='standard',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_deadlines',
                    to='portal.platformuser',
                )),
                ('student', models.ForeignKey(
                    limit_choices_to={'role': 'student'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='deadlines',
                    to='portal.platformuser',
                )),
            ],
            options={
                'verbose_name': 'Deadline',
                'verbose_name_plural': 'Deadlines',
                'ordering': ['due_at'],
            },
        ),
    ]
