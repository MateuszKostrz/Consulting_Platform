from django.db import migrations, models


TIMEZONES = [
    'Europe/Warsaw',
    'Europe/London',
    'Europe/Amsterdam',
    'Europe/Berlin',
    'America/New_York',
    'America/Los_Angeles',
    'Asia/Tokyo',
    'Asia/Singapore',
    'Australia/Sydney',
    'UTC',
]


def assign_deadline_timezones(apps, schema_editor):
    Deadline = apps.get_model('portal', 'Deadline')
    deadlines = list(Deadline.objects.order_by('id'))
    for index, deadline in enumerate(deadlines):
        deadline.timezone = TIMEZONES[index % len(TIMEZONES)]
        deadline.save(update_fields=['timezone'])


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0014_personalprofile_parent_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='deadline',
            name='timezone',
            field=models.CharField(
                choices=[
                    ('Europe/Warsaw', 'Warsaw (CET)'),
                    ('Europe/London', 'London (GMT/BST)'),
                    ('Europe/Amsterdam', 'Amsterdam (CET)'),
                    ('Europe/Berlin', 'Berlin (CET)'),
                    ('Europe/Paris', 'Paris (CET)'),
                    ('America/New_York', 'New York (ET)'),
                    ('America/Los_Angeles', 'Los Angeles (PT)'),
                    ('Asia/Tokyo', 'Tokyo (JST)'),
                    ('Asia/Singapore', 'Singapore (SGT)'),
                    ('Australia/Sydney', 'Sydney (AEST)'),
                    ('UTC', 'UTC'),
                ],
                default='Europe/Warsaw',
                max_length=64,
            ),
        ),
        migrations.RunPython(assign_deadline_timezones, migrations.RunPython.noop),
    ]
