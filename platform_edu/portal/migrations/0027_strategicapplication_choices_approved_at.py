from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0026_universitychoice_country_sort_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='strategicapplication',
            name='choices_approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
