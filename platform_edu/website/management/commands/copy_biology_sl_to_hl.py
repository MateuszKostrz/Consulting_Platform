from django.core.management.base import BaseCommand
from website.models import Biology_SL_Questionbank, Biology_HL_Questionbank
from django.db import transaction


class Command(BaseCommand):
    help = 'Copy overlapping questions from Biology SL to Biology HL questionbank'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be copied without actually copying',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force copy even if question might already exist',
        )
    
    def handle(self, *args, **options):
        # Define overlapping chapters between SL and HL
        sl_chapters = [choice[0] for choice in Biology_SL_Questionbank.CHAPTERS]
        hl_chapters = [choice[0] for choice in Biology_HL_Questionbank.CHAPTERS]
        
        # Find overlapping chapters
        overlapping_chapters = set(sl_chapters) & set(hl_chapters)
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {len(overlapping_chapters)} overlapping chapters:')
        )
        for chapter in sorted(overlapping_chapters):
            self.stdout.write(f'  - {chapter}')
        
        # Get all SL questions from overlapping chapters
        sl_questions = Biology_SL_Questionbank.objects.filter(
            chapter__in=overlapping_chapters
        ).order_by('chapter', 'id')
        
        self.stdout.write(
            self.style.WARNING(f'\nFound {sl_questions.count()} SL questions in overlapping chapters')
        )
        
        copied_count = 0
        skipped_count = 0
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Process each question
        for sl_question in sl_questions:
            # Check if question already exists in HL (based on question text and chapter)
            existing_hl = Biology_HL_Questionbank.objects.filter(
                question=sl_question.question,
                chapter=sl_question.chapter
            ).first()
            
            if existing_hl and not options['force']:
                if options['dry_run']:
                    self.stdout.write(f'  SKIP: Question already exists in HL - Chapter: {sl_question.chapter}')
                skipped_count += 1
                continue
            
            if options['dry_run']:
                self.stdout.write(
                    f'  COPY: Question from chapter "{sl_question.chapter}" '
                    f'(Difficulty: {sl_question.difficulty}, Paper: {sl_question.paper})'
                )
                copied_count += 1
            else:
                # Copy question to HL
                try:
                    with transaction.atomic():
                        if existing_hl and options['force']:
                            # Update existing question
                            existing_hl.answer = sl_question.answer
                            existing_hl.difficulty = sl_question.difficulty
                            existing_hl.paper = sl_question.paper
                            existing_hl.correct_answer = sl_question.correct_answer
                            existing_hl.video = sl_question.video
                            existing_hl.marks = sl_question.marks
                            existing_hl.type = sl_question.type
                            existing_hl.save()
                            self.stdout.write(
                                f'  UPDATED: Question in chapter "{sl_question.chapter}"'
                            )
                        else:
                            # Create new question
                            Biology_HL_Questionbank.objects.create(
                                question=sl_question.question,
                                answer=sl_question.answer,
                                difficulty=sl_question.difficulty,
                                paper=sl_question.paper,
                                correct_answer=sl_question.correct_answer,
                                video=sl_question.video,
                                chapter=sl_question.chapter,
                                marks=sl_question.marks,
                                type=sl_question.type
                            )
                            self.stdout.write(
                                f'  COPIED: Question to chapter "{sl_question.chapter}"'
                            )
                        copied_count += 1
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ERROR: Failed to copy question - {str(e)}')
                    )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN SUMMARY:')
            )
            self.stdout.write(f'  Would copy: {copied_count} questions')
            self.stdout.write(f'  Would skip: {skipped_count} questions (already exist)')
            self.stdout.write(f'  Total SL questions: {sl_questions.count()}')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'COPY COMPLETED:')
            )
            self.stdout.write(f'  Copied: {copied_count} questions')
            self.stdout.write(f'  Skipped: {skipped_count} questions (already exist)')
            self.stdout.write(f'  Total SL questions: {sl_questions.count()}')
        
        # Show chapter breakdown
        self.stdout.write('\nChapter breakdown:')
        for chapter in sorted(overlapping_chapters):
            count = sl_questions.filter(chapter=chapter).count()
            self.stdout.write(f'  {chapter}: {count} questions')
        
        if not options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS('\n✅ Questions successfully copied to Biology HL!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\n💡 Run without --dry-run to actually copy the questions')
            ) 