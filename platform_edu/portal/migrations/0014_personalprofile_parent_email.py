from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0013_offers_offer'),
    ]

    operations = [
        migrations.AddField(
            model_name='personalprofile',
            name='parent_email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
    ]
