from django.core.management.base import BaseCommand
from django.db import transaction
from website.models import Math_AA_SL_Questionbank, Math_AA_HL_Questionbank


class Command(BaseCommand):
    help = 'Copy overlapping questions from Math_AA_SL_Questionbank to Math_AA_HL_Questionbank'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be copied without actually copying',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )
        parser.add_argument(
            '--clear-hl',
            action='store_true',
            help='Clear HL table before copying',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        clear_hl = options['clear_hl']

        # Get the chapter choices for both models
        sl_chapters = dict(Math_AA_SL_Questionbank.CHAPTERS)
        hl_chapters = dict(Math_AA_HL_Questionbank.CHAPTERS)
        
        # Define chapter mappings for topics with different names
        chapter_mappings = {
            'integration': 'integral_calculus',
            'differentiation': 'differential_calculus'
        }
        
        # Find overlapping chapters (direct matches)
        overlapping_chapters = set(sl_chapters.keys()) & set(hl_chapters.keys())
        
        # Add mapped chapters
        mapped_chapters = {}
        for sl_chapter, hl_chapter in chapter_mappings.items():
            if sl_chapter in sl_chapters and hl_chapter in hl_chapters:
                mapped_chapters[sl_chapter] = hl_chapter
                overlapping_chapters.add(sl_chapter)  # Include SL chapter in processing
        
        self.stdout.write(f"SL has {len(sl_chapters)} chapters")
        self.stdout.write(f"HL has {len(hl_chapters)} chapters") 
        self.stdout.write(f"Found {len(overlapping_chapters)} chapters to copy:")
        
        # Show direct matches
        direct_matches = overlapping_chapters - set(mapped_chapters.keys())
        for chapter in sorted(direct_matches):
            self.stdout.write(f"  - {chapter}: {sl_chapters[chapter]}")
            
        # Show mapped chapters
        if mapped_chapters:
            self.stdout.write(f"\nChapter mappings:")
            for sl_chapter, hl_chapter in mapped_chapters.items():
                self.stdout.write(f"  - {sl_chapter} → {hl_chapter}: {sl_chapters[sl_chapter]} → {hl_chapters[hl_chapter]}")

        # Get counts
        total_sl_questions = Math_AA_SL_Questionbank.objects.count()
        overlapping_sl_questions = Math_AA_SL_Questionbank.objects.filter(chapter__in=overlapping_chapters).count()
        current_hl_questions = Math_AA_HL_Questionbank.objects.count()

        self.stdout.write(f"\nTotal SL questions: {total_sl_questions}")
        self.stdout.write(f"SL questions in overlapping chapters: {overlapping_sl_questions}")
        self.stdout.write(f"Current HL questions: {current_hl_questions}")

        if overlapping_sl_questions == 0:
            self.stdout.write(self.style.WARNING("No overlapping questions found. Nothing to copy."))
            return

        # Confirmation prompt
        if not force and not dry_run:
            if clear_hl and current_hl_questions > 0:
                confirm = input(f"This will DELETE {current_hl_questions} existing HL questions and copy {overlapping_sl_questions} SL questions. Continue? (yes/no): ")
            else:
                confirm = input(f"This will copy {overlapping_sl_questions} SL questions to HL table. Continue? (yes/no): ")
            
            if confirm.lower() != 'yes':
                self.stdout.write("Operation cancelled.")
                return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No actual changes will be made"))
            if clear_hl:
                self.stdout.write(f"Would delete {current_hl_questions} existing HL questions")
            self.stdout.write(f"Would copy {overlapping_sl_questions} SL questions to HL table")
            
            # Show breakdown by chapter
            for chapter in sorted(overlapping_chapters):
                count = Math_AA_SL_Questionbank.objects.filter(chapter=chapter).count()
                if chapter in mapped_chapters:
                    target_chapter = mapped_chapters[chapter]
                    self.stdout.write(f"  {chapter} → {target_chapter}: {count} questions")
                else:
                    self.stdout.write(f"  {chapter}: {count} questions")
            return

        # Perform the copy operation
        try:
            with transaction.atomic():
                # Clear HL table if requested
                if clear_hl:
                    deleted_count = Math_AA_HL_Questionbank.objects.count()
                    Math_AA_HL_Questionbank.objects.all().delete()
                    self.stdout.write(f"Deleted {deleted_count} existing HL questions")

                # Copy overlapping questions
                copied_count = 0
                
                sl_questions = Math_AA_SL_Questionbank.objects.filter(chapter__in=overlapping_chapters)
                
                for question in sl_questions:
                    # Determine the target chapter (use mapping if exists)
                    target_chapter = mapped_chapters.get(question.chapter, question.chapter)
                    
                    # Check if question already exists (unless we cleared the table)
                    if not clear_hl:
                        existing = Math_AA_HL_Questionbank.objects.filter(
                            question=question.question,
                            chapter=target_chapter
                        ).exists()
                        if existing:
                            continue  # Skip duplicates
                    
                    Math_AA_HL_Questionbank.objects.create(
                        question=question.question,
                        answer=question.answer,
                        difficulty=question.difficulty,
                        paper=question.paper,
                        video=question.video,
                        chapter=target_chapter,  # Use mapped chapter
                        marks=question.marks,
                        type=question.type,
                    )
                    copied_count += 1
                    
                    if copied_count % 50 == 0:
                        self.stdout.write(f"Copied {copied_count} questions...")

                action = "Added" if clear_hl else "Copied"
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully {action.lower()} {copied_count} questions to Math_AA_HL_Questionbank")
                )
                
                final_count = Math_AA_HL_Questionbank.objects.count()
                self.stdout.write(f"Final HL question count: {final_count}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during copy operation: {str(e)}")
            )
            raise 