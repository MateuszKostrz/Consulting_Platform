from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0039_universitychoice_comments'),
    ]

    operations = [
        migrations.AddField(
            model_name='universitychoice',
            name='comments_preview_rows',
            field=models.PositiveSmallIntegerField(default=4),
        ),
    ]
