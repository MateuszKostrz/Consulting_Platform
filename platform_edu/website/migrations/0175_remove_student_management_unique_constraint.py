# Generated manually to remove unique constraint that prevents same student with multiple tutors

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0174_alter_studentmanagement_unique_together'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='studentmanagement',
            unique_together=set(),
        ),
    ]

