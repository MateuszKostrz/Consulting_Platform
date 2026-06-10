"""
Django management command to update video access levels for past papers by year.

Usage:
    python manage.py update_video_access --subject math_ai_sl
    python manage.py update_video_access --subject math_ai_hl --dry-run
    python manage.py update_video_access --all-subjects

Logic:
- Around 5 videos: 1 free, rest premium
- Around 10-20 videos: 1 free, 1 registered, rest premium  
- 20+ videos: 3 free, 3 registered, rest premium
"""

from django.core.management.base import BaseCommand, CommandError
from website.models import (
    Past_Paper_Videos,
    Past_Paper_Videos_AI_HL,
    Past_Paper_Videos_AA_SL,
    Past_Paper_Videos_AA_HL,
    Past_Paper_Videos_Physics_SL,
    Past_Paper_Videos_Physics_HL
)
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════
# 📝 CONFIGURATION - CHANGE THIS TO SELECT WHICH SUBJECT TO UPDATE
# ═══════════════════════════════════════════════════════════════════
# Options: 'math_ai_sl', 'math_ai_hl', 'math_aa_sl', 'math_aa_hl', 'physics_sl', 'physics_hl'
SELECTED_SUBJECT = 'physics_hl'  # ← CHANGE THIS LINE
# ═══════════════════════════════════════════════════════════════════


class Command(BaseCommand):
    help = 'Update video access levels for past papers based on video count per session'

    # Map of available subjects
    SUBJECT_MODELS = {
        'math_ai_sl': Past_Paper_Videos,
        'math_ai_hl': Past_Paper_Videos_AI_HL,
        'math_aa_sl': Past_Paper_Videos_AA_SL,
        'math_aa_hl': Past_Paper_Videos_AA_HL,
        'physics_sl': Past_Paper_Videos_Physics_SL,
        'physics_hl': Past_Paper_Videos_Physics_HL,
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--year',
            type=str,
            help='Only update videos for a specific year (e.g., 2024)',
        )

    def handle(self, *args, **options):
        # Use the subject selected at the top of the file
        subject = SELECTED_SUBJECT
        
        dry_run = options['dry_run']
        specific_year = options['year']

        if dry_run:
            self.stdout.write(self.style.WARNING('🧪 DRY RUN MODE - No changes will be saved\n'))

        # Validate subject selection
        if subject not in self.SUBJECT_MODELS:
            self.stderr.write(self.style.ERROR(f"Invalid subject: {subject}"))
            self.stdout.write(f"Please set SELECTED_SUBJECT to one of: {list(self.SUBJECT_MODELS.keys())}")
            return

        # Display which subject is being processed
        subject_names = {
            'math_ai_sl': 'MATH AI SL',
            'math_ai_hl': 'MATH AI HL',
            'math_aa_sl': 'MATH AA SL',
            'math_aa_hl': 'MATH AA HL',
            'physics_sl': 'PHYSICS SL',
            'physics_hl': 'PHYSICS HL',
        }
        subject_name = subject_names.get(subject, subject.upper())
        self.stdout.write(self.style.SUCCESS(f'\n📚 Processing: {subject_name} (by session)'))
        self.update_subject_videos(subject, dry_run, specific_year)

        if not dry_run:
            self.stdout.write(self.style.SUCCESS('\n✅ All updates completed!'))
        else:
            self.stdout.write(self.style.WARNING('\n✅ Dry run completed! Run without --dry-run to apply changes.'))

    def update_subject_videos(self, subject, dry_run=False, specific_year=None):
        """Update video access levels for a specific subject"""
        Model = self.SUBJECT_MODELS[subject]
        
        # Group videos by session (month + year + timezone + paper)
        videos_by_session = defaultdict(list)
        
        # Get all videos, optionally filtered by year
        if specific_year:
            videos = Model.objects.filter(year=specific_year)
        else:
            videos = Model.objects.all()
        
        # Group by session (e.g., "May 2025 TZ1 P1")
        for video in videos:
            session_key = f"{video.month}{video.year}TZ{video.time_zone}P{video.paper}"
            videos_by_session[session_key].append(video)
        
        # Process each session
        total_updated = 0
        for session_key in sorted(videos_by_session.keys()):
            session_videos = videos_by_session[session_key]
            
            # IMPORTANT: Sort by question NUMBER (not ID)
            # Convert question field to int for proper sorting (Q1, Q2, Q3... not Q1, Q10, Q2...)
            try:
                session_videos = sorted(session_videos, key=lambda v: int(v.question))
            except (ValueError, TypeError):
                # If question isn't a number, sort alphabetically as fallback
                session_videos = sorted(session_videos, key=lambda v: v.question)
            
            video_count = len(session_videos)
            
            # Extract readable session name for display
            first_video = session_videos[0]
            session_display = f"{first_video.month} {first_video.year} TZ{first_video.time_zone} P{first_video.paper}"
            
            self.stdout.write(f'\n  📄 {session_display}: {video_count} videos')
            
            # Determine access level distribution based on count
            free_count, registered_count = self.calculate_access_distribution(video_count)
            
            self.stdout.write(f'     → {free_count} free, {registered_count} registered, {video_count - free_count - registered_count} premium')
            
            # Show which questions get which access level
            if video_count > 0:
                free_questions = [session_videos[i].question for i in range(min(free_count, video_count))]
                registered_questions = [session_videos[i].question for i in range(free_count, min(free_count + registered_count, video_count))]
                self.stdout.write(f'     Free: Q{", Q".join(free_questions)}')
                if registered_questions:
                    self.stdout.write(f'     Registered: Q{", Q".join(registered_questions)}')
            
            # Update videos (now properly sorted by question number)
            updates = self.assign_access_levels(session_videos, free_count, registered_count, dry_run)
            total_updated += updates
            
            if dry_run:
                self.stdout.write(f'     Would update: {updates} videos')
            else:
                self.stdout.write(self.style.SUCCESS(f'     ✓ Updated: {updates} videos'))
        
        return total_updated

    def calculate_access_distribution(self, video_count):
        """
        Calculate how many videos should be free and registered.
        Returns: (free_count, registered_count)
        """
        if video_count <= 5:
            # Around 5 videos: 1 free, rest premium
            return (1, 0)
        elif video_count <= 20:
            # Around 10-20 videos: 1 free, 1 registered, rest premium
            return (1, 1)
        else:
            # 20+ videos: 3 free, 3 registered, rest premium
            return (3, 3)

    def assign_access_levels(self, videos, free_count, registered_count, dry_run=False):
        """
        Assign access levels to videos and save.
        Returns number of videos updated.
        """
        updated_count = 0
        
        for i, video in enumerate(videos):
            # Determine access level for this video
            if i < free_count:
                access_level = 'free'
            elif i < free_count + registered_count:
                access_level = 'registered'
            else:
                access_level = 'premium'
            
            # Check if video needs updating
            current_access = getattr(video, 'access_level', None)
            
            if current_access != access_level:
                if not dry_run:
                    video.access_level = access_level
                    video.save()
                updated_count += 1
        
        return updated_count

    def get_video_display_name(self, video):
        """Get a readable display name for the video"""
        return f"{video.month} {video.year} TZ{video.time_zone} P{video.paper} Q{video.question}"

