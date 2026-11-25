from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0048_studentdocument_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deadline',
            name='student',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'role': 'student'},
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='deadlines',
                to='portal.platformuser',
            ),
        ),
    ]