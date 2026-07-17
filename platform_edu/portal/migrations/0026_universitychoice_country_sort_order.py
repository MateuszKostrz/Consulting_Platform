from django.db import migrations, models


def set_initial_sort_order(apps, schema_editor):
    UniversityChoice = apps.get_model('portal', 'UniversityChoice')
    profile_ids = (
        UniversityChoice.objects.order_by()
        .values_list('personal_profile_id', flat=True)
        .distinct()
    )
    for profile_id in profile_ids:
        for index, choice in enumerate(
            UniversityChoice.objects.filter(personal_profile_id=profile_id).order_by('id'),
            start=1,
        ):
            choice.sort_order = index
            choice.save(update_fields=['sort_order'])


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0025_studentsectionaccess'),
    ]

    operations = [
        migrations.AddField(
            model_name='universitychoice',
            name='country',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='universitychoice',
            name='sort_order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name='universitychoice',
            options={
                'ordering': ['sort_order', 'id'],
                'verbose_name': 'University Choice',
                'verbose_name_plural': 'University Choices',
            },
        ),
        migrations.RunPython(set_initial_sort_order, migrations.RunPython.noop),
    ]
