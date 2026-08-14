from django.db import migrations


def backfill_personal_email(apps, schema_editor):
    PersonalProfile = apps.get_model('portal', 'PersonalProfile')
    profiles = PersonalProfile.objects.filter(
        platform_user__isnull=False,
        personal_email='',
    ).select_related('platform_user')

    for profile in profiles.iterator():
        login_email = profile.platform_user.email
        if login_email:
            profile.personal_email = login_email
            profile.save(update_fields=['personal_email'])


class Migration(migrations.Migration):
    dependencies = [
        ('portal', '0036_remove_portfoliodesign_checklist_approved_at'),
    ]

    operations = [
        migrations.RunPython(backfill_personal_email, migrations.RunPython.noop),
    ]
