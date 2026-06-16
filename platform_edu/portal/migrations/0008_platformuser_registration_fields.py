from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0007_deadline'),
    ]

    operations = [
        migrations.AddField(
            model_name='platformuser',
            name='application_type',
            field=models.CharField(
                blank=True,
                choices=[('bachelor', 'Bachelor'), ('masters', 'Masters'), ('phd', 'PhD')],
                default='',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='platformuser',
            name='role',
            field=models.CharField(
                choices=[('student', 'Student'), ('parent', 'Parent'), ('admin', 'Admin')],
                default='student',
                max_length=20,
            ),
        ),
    ]
