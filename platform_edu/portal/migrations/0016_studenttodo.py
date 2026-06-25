from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0015_deadline_timezone'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentTodo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('due_date', models.DateField()),
                ('link', models.URLField(blank=True, default='', max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_todos',
                    to='portal.platformuser',
                )),
                ('student', models.ForeignKey(
                    limit_choices_to={'role': 'student'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='todos',
                    to='portal.platformuser',
                )),
            ],
            options={
                'verbose_name': 'Student to-do',
                'verbose_name_plural': 'Student to-dos',
                'ordering': ['due_date', 'name'],
            },
        ),
    ]
