from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PersonalProfile, PlatformUser

User = get_user_model()


@receiver(post_save, sender=User)
def sync_platform_user_from_auth_user(sender, instance, **kwargs):
    try:
        platform_user = instance.platform_account
    except PlatformUser.DoesNotExist:
        return
    platform_user.sync_from_user()
    platform_user.save(update_fields=[
        'first_name',
        'last_name',
        'email',
        'account_created_at',
        'updated_at',
    ])


@receiver(post_save, sender=PlatformUser)
def ensure_student_personal_profile_exists(sender, instance, **kwargs):
    if instance.role != PlatformUser.Role.STUDENT:
        return
    PersonalProfile.objects.get_or_create(
        platform_user=instance,
        defaults={
            'session_key': None,
            'edunade_email': instance.email,
        },
    )
