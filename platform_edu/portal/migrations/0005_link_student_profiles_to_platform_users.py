from django.db import migrations


def link_student_profiles(apps, schema_editor):
    PlatformUser = apps.get_model('portal', 'PlatformUser')
    PersonalProfile = apps.get_model('portal', 'PersonalProfile')

    for platform_user in PlatformUser.objects.filter(role='student'):
        profile, created = PersonalProfile.objects.get_or_create(
            platform_user=platform_user,
            defaults={
                'session_key': None,
                'edunade_email': platform_user.email,
            },
        )
        if not profile.edunade_email and platform_user.email:
            profile.edunade_email = platform_user.email
            profile.save(update_fields=['edunade_email'])


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0004_platformuser_identity_fields'),
    ]

    operations = [
        migrations.RunPython(link_student_profiles, migrations.RunPython.noop),
    ]
