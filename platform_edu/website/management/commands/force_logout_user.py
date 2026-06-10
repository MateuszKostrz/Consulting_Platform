from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.utils import timezone
from importlib import import_module
from django.conf import settings


class Command(BaseCommand):
    help = 'Force logout a user by deleting all their active sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address of the user to force logout'
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        
        # Find the Django User with this email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No user found with email: {email}'))
            return
        
        # Get the session engine
        engine = import_module(settings.SESSION_ENGINE)
        
        # Find and delete all sessions belonging to this user
        deleted_count = 0
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        
        for session in active_sessions:
            session_data = session.get_decoded()
            # Check if this session belongs to the target user
            # Check both standard Django auth and custom session email storage
            if (session_data.get('_auth_user_id') == str(user.id) or 
                session_data.get('email', '').lower() == email):
                session.delete()
                deleted_count += 1
        
        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully logged out user "{email}".\n'
                    f'Deleted {deleted_count} active session(s).'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'User "{email}" found but no active sessions were deleted.\n'
                    f'The user may already be logged out.'
                )
            )

