from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0038_studentdocument'),
    ]

    operations = [
        migrations.AddField(
            model_name='universitychoice',
            name='comments',
            field=models.TextField(blank=True, default=''),
        ),
    ]
