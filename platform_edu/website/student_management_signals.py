from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import StudentManagement, TutorSession, Users
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=StudentManagement)
def store_old_values(sender, instance, **kwargs):
    """Store old values before saving to detect changes"""
    if instance.pk:
        try:
            old_instance = StudentManagement.objects.get(pk=instance.pk)
            instance._old_student_email = old_instance.student_email
            instance._old_linked_user_email = old_instance.linked_user.email if old_instance.linked_user else None
            instance._old_first_name = old_instance.student_first_name
            instance._old_last_name = old_instance.student_last_name
        except StudentManagement.DoesNotExist:
            pass


@receiver(post_save, sender=StudentManagement)
def sync_student_changes_to_sessions(sender, instance, created, **kwargs):
    """
    Automatically update all TutorSession records when StudentManagement details change.
    This ensures sessions display correctly even after name/email changes.
    """
    if created:
        # New student, no sessions to update yet
        return
    
    try:
        # Determine the current email
        current_email = None
        if instance.linked_user:
            current_email = instance.linked_user.email
        elif instance.student_email:
            current_email = instance.student_email
        
        # Determine the old email
        old_email = getattr(instance, '_old_student_email', None)
        old_linked_email = getattr(instance, '_old_linked_user_email', None)
        
        # The old email is either the old linked user email or the old student_email
        search_email = old_linked_email if old_linked_email else old_email
        
        if not search_email:
            # No old email to search for
            logger.info(f"No old email found for StudentManagement {instance.id}, skipping session update")
            return
        
        # Find all sessions with the old email
        sessions_to_update = TutorSession.objects.filter(student_email=search_email)
        
        if not sessions_to_update.exists():
            logger.info(f"No sessions found for email {search_email}")
            return
        
        # Update all matching sessions
        update_count = sessions_to_update.update(
            student_email=current_email,
            student_first_name=instance.student_first_name,
            student_last_name=instance.student_last_name
        )
        
        logger.info(
            f"✓ Updated {update_count} sessions for {instance.student_first_name} {instance.student_last_name} "
            f"(email changed from {search_email} to {current_email})"
        )
        
    except Exception as e:
        logger.error(f"Error syncing student changes to sessions: {e}")


@receiver(pre_save, sender=Users)
def store_old_user_email(sender, instance, **kwargs):
    """Store old email before saving Users record"""
    if instance.pk:
        try:
            old_user = Users.objects.get(pk=instance.pk)
            instance._old_email = old_user.email
        except Users.DoesNotExist:
            pass


@receiver(post_save, sender=Users)
def sync_user_email_changes_to_sessions(sender, instance, created, **kwargs):
    """
    When a User's email changes, update all TutorSession records for students linked to that user.
    This handles cases where the student has a linked_user in StudentManagement.
    """
    if created:
        return
    
    try:
        old_email = getattr(instance, '_old_email', None)
        new_email = instance.email
        
        # Check if email actually changed
        if not old_email or old_email == new_email:
            return
        
        # Find all StudentManagement records linked to this user
        linked_students = StudentManagement.objects.filter(linked_user=instance)
        
        if not linked_students.exists():
            return
        
        # Update sessions for this user
        sessions_to_update = TutorSession.objects.filter(student_email=old_email)
        
        if sessions_to_update.exists():
            update_count = sessions_to_update.update(
                student_email=new_email,
                student_first_name=instance.first_name,
                student_last_name=instance.last_name
            )
            
            logger.info(
                f"✓ Updated {update_count} sessions due to Users email change "
                f"from {old_email} to {new_email} for {instance.first_name} {instance.last_name}"
            )
        
    except Exception as e:
        logger.error(f"Error syncing user email changes to sessions: {e}")

