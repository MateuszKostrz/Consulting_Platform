from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0046_academicprofile_personal_statement_assessment'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentsectionaccess',
            name='self_assessment',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]