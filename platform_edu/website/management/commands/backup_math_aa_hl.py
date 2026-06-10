from django.core.management.base import BaseCommand
from django.db import transaction
from website.models import Math_AA_HL_Questionbank, Math_AA_HL_Questionbank_Backup


class Command(BaseCommand):
    help = 'Copy all questions from Math_AA_HL_Questionbank to Math_AA_HL_Questionbank_Backup'

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
            '--clear-backup',
            action='store_true',
            help='Clear backup table before copying',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        clear_backup = options['clear_backup']

        # Get count of source questions
        source_count = Math_AA_HL_Questionbank.objects.count()
        backup_count = Math_AA_HL_Questionbank_Backup.objects.count()

        self.stdout.write(f"Found {source_count} questions in Math_AA_HL_Questionbank")
        self.stdout.write(f"Found {backup_count} questions in Math_AA_HL_Questionbank_Backup")

        if source_count == 0:
            self.stdout.write(self.style.WARNING("No questions found in source table. Nothing to copy."))
            return

        # Confirmation prompt
        if not force and not dry_run:
            if clear_backup and backup_count > 0:
                confirm = input(f"This will DELETE {backup_count} existing backup questions and copy {source_count} new ones. Continue? (yes/no): ")
            else:
                confirm = input(f"This will copy {source_count} questions to backup table. Continue? (yes/no): ")
            
            if confirm.lower() != 'yes':
                self.stdout.write("Operation cancelled.")
                return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No actual changes will be made"))
            if clear_backup:
                self.stdout.write(f"Would delete {backup_count} existing backup questions")
            self.stdout.write(f"Would copy {source_count} questions to backup table")
            return

        # Perform the copy operation
        try:
            with transaction.atomic():
                # Clear backup table if requested
                if clear_backup:
                    deleted_count = Math_AA_HL_Questionbank_Backup.objects.count()
                    Math_AA_HL_Questionbank_Backup.objects.all().delete()
                    self.stdout.write(f"Deleted {deleted_count} existing backup questions")

                # Copy all questions
                copied_count = 0
                
                for question in Math_AA_HL_Questionbank.objects.all():
                    Math_AA_HL_Questionbank_Backup.objects.create(
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
                    
                    if copied_count % 100 == 0:
                        self.stdout.write(f"Copied {copied_count} questions...")

                self.stdout.write(
                    self.style.SUCCESS(f"Successfully copied {copied_count} questions to Math_AA_HL_Questionbank_Backup")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during copy operation: {str(e)}")
            )
            raise 