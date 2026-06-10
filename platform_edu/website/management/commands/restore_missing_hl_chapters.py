from django.core.management.base import BaseCommand
from django.db import transaction
from website.models import Math_AA_HL_Questionbank, Math_AA_HL_Questionbank_Backup


class Command(BaseCommand):
    help = 'Copy HL-specific chapters from backup that are missing in current HL'

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

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        # Get all chapters that exist in backup
        backup_chapters = set(Math_AA_HL_Questionbank_Backup.objects.values_list('chapter', flat=True).distinct())
        
        # Get all chapters that exist in current HL
        current_hl_chapters = set(Math_AA_HL_Questionbank.objects.values_list('chapter', flat=True).distinct())
        
        # Find chapters that are in backup but missing from current HL
        missing_chapters = backup_chapters - current_hl_chapters
        
        self.stdout.write(f"Backup has {len(backup_chapters)} chapters: {sorted(backup_chapters)}")
        self.stdout.write(f"Current HL has {len(current_hl_chapters)} chapters: {sorted(current_hl_chapters)}")
        self.stdout.write(f"Missing chapters (in backup but not in current HL): {sorted(missing_chapters)}")
        
        if not missing_chapters:
            self.stdout.write(self.style.SUCCESS("No missing chapters found. All backup chapters are already in current HL."))
            return
        
        # Count questions in missing chapters
        questions_to_copy = 0
        chapter_breakdown = {}
        
        for chapter in missing_chapters:
            count = Math_AA_HL_Questionbank_Backup.objects.filter(chapter=chapter).count()
            chapter_breakdown[chapter] = count
            questions_to_copy += count
            
        self.stdout.write(f"\nQuestions to copy from missing chapters:")
        for chapter, count in sorted(chapter_breakdown.items()):
            self.stdout.write(f"  {chapter}: {count} questions")
        self.stdout.write(f"Total questions to copy: {questions_to_copy}")
        
        if questions_to_copy == 0:
            self.stdout.write(self.style.WARNING("No questions found in missing chapters."))
            return

        # Confirmation prompt
        if not force and not dry_run:
            confirm = input(f"This will copy {questions_to_copy} questions from {len(missing_chapters)} missing chapters from backup to current HL. Continue? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write("Operation cancelled.")
                return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No actual changes will be made"))
            self.stdout.write(f"Would copy {questions_to_copy} questions from backup to current HL")
            return

        # Perform the copy operation
        try:
            with transaction.atomic():
                copied_count = 0
                
                for chapter in missing_chapters:
                    backup_questions = Math_AA_HL_Questionbank_Backup.objects.filter(chapter=chapter)
                    
                    for question in backup_questions:
                        Math_AA_HL_Questionbank.objects.create(
                            question=question.question,
                            answer=question.answer,
                            difficulty=question.difficulty,
                            paper=question.paper,
                            video=question.video,
                            chapter=question.chapter,
                            marks=question.marks,
                            type=question.type,
                        )
                        copied_count += 1
                        
                        if copied_count % 25 == 0:
                            self.stdout.write(f"Copied {copied_count} questions...")

                self.stdout.write(
                    self.style.SUCCESS(f"Successfully copied {copied_count} questions from missing chapters")
                )
                
                final_count = Math_AA_HL_Questionbank.objects.count()
                final_chapters = Math_AA_HL_Questionbank.objects.values_list('chapter', flat=True).distinct().count()
                self.stdout.write(f"Final HL question count: {final_count}")
                self.stdout.write(f"Final HL chapter count: {final_chapters}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during copy operation: {str(e)}")
            )
            raise 