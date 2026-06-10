"""
Django Management Command: Copy Biology SL questions to Biology HL

This command copies Biology SL questions to Biology HL chapters where they don't already exist.
- All existing Biology SL questions remain unchanged
- Biology HL questions are not deleted, only new ones are added
- Only copies questions from chapters that exist in both SL and HL
- Avoids duplicates by checking question text content
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from website.models import Biology_SL_Questionbank, Biology_HL_Questionbank
import hashlib

class Command(BaseCommand):
    help = 'Copy Biology SL questions to Biology HL chapters where they don\'t already exist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Show analysis of chapters and question counts without copying',
        )
        parser.add_argument(
            '--copy',
            action='store_true',
            help='Perform the actual copy operation',
        )
        parser.add_argument(
            '--chapter',
            type=str,
            help='Copy questions from a specific chapter only',
        )

    def handle(self, *args, **options):
        if options['analyze']:
            self.show_chapter_analysis()
        elif options['copy']:
            specific_chapter = options.get('chapter')
            self.copy_hl_questions_to_sl(specific_chapter)
        else:
            self.stdout.write(self.style.WARNING('Usage:'))
            self.stdout.write('  python manage.py copy_biology_hl_to_sl --analyze    # Show analysis')
            self.stdout.write('  python manage.py copy_biology_hl_to_sl --copy       # Copy SL to HL')
            self.stdout.write('  python manage.py copy_biology_hl_to_sl --copy --chapter water  # Copy specific chapter')

    def get_common_chapters(self):
        """
        Get chapters that exist in both Biology SL and HL
        """
        # Extract chapter choices from both models
        sl_chapters = dict(Biology_SL_Questionbank.CHAPTERS)
        hl_chapters = dict(Biology_HL_Questionbank.CHAPTERS)
        
        # Find common chapters (those that exist in both SL and HL)
        common_chapters = []
        for sl_chapter_key, sl_chapter_name in sl_chapters.items():
            if sl_chapter_key in hl_chapters:
                common_chapters.append((sl_chapter_key, sl_chapter_name))
        
        return common_chapters

    def get_question_hash(self, question_text):
        """
        Create a hash of the question text for duplicate detection
        """
        # Clean the question text (remove extra whitespace, convert to lowercase)
        cleaned_text = ' '.join(question_text.strip().lower().split())
        return hashlib.md5(cleaned_text.encode()).hexdigest()

    def check_question_exists_in_hl(self, question_text, chapter):
        """
        Check if a similar question already exists in Biology HL for the given chapter
        """
        question_hash = self.get_question_hash(question_text)
        
        # Check all HL questions in this chapter
        hl_questions = Biology_HL_Questionbank.objects.filter(chapter=chapter)
        
        for hl_question in hl_questions:
            hl_hash = self.get_question_hash(hl_question.question)
            if hl_hash == question_hash:
                return True
        
        return False

    def copy_hl_questions_to_sl(self, specific_chapter=None):
        """
        Main function to copy Biology SL questions to Biology HL
        """
        self.stdout.write(self.style.SUCCESS('🧬 Biology SL to HL Question Copy Command'))
        self.stdout.write('=' * 50)
        
        # Get common chapters
        common_chapters = self.get_common_chapters()
        
        # Filter for specific chapter if requested
        if specific_chapter:
            common_chapters = [(k, v) for k, v in common_chapters if k == specific_chapter]
            if not common_chapters:
                self.stdout.write(self.style.ERROR(f'❌ Chapter "{specific_chapter}" not found in common chapters'))
                return
            self.stdout.write(f"📋 Processing specific chapter: {specific_chapter}")
        else:
            self.stdout.write(f"📋 Found {len(common_chapters)} common chapters between SL and HL:")
            for chapter_key, chapter_name in common_chapters:
                self.stdout.write(f"   • {chapter_name} ({chapter_key})")
        
        self.stdout.write("\n🔍 Analyzing questions...")
        
        total_copied = 0
        total_skipped = 0
        
        # Process each common chapter
        for chapter_key, chapter_name in common_chapters:
            self.stdout.write(f"\n📖 Processing chapter: {chapter_name}")
            
            # Get all SL questions for this chapter
            sl_questions = Biology_SL_Questionbank.objects.filter(chapter=chapter_key)
            chapter_copied = 0
            chapter_skipped = 0
            
            if sl_questions.count() == 0:
                self.stdout.write(f"   ⚠️  No SL questions found for this chapter")
                continue
            
            with transaction.atomic():
                for sl_question in sl_questions:
                    # Check if this question already exists in HL
                    if self.check_question_exists_in_hl(sl_question.question, chapter_key):
                        chapter_skipped += 1
                        continue
                    
                    # Create new HL question from SL question
                    new_hl_question = Biology_HL_Questionbank.objects.create(
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
                    
                    chapter_copied += 1
            
            self.stdout.write(f"   ✅ Copied: {chapter_copied} questions")
            self.stdout.write(f"   ⏭️  Skipped: {chapter_skipped} questions (already exist)")
            
            total_copied += chapter_copied
            total_skipped += chapter_skipped
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("📊 SUMMARY:"))
        self.stdout.write(f"✅ Total questions copied: {total_copied}")
        self.stdout.write(f"⏭️  Total questions skipped: {total_skipped}")
        self.stdout.write(f"📚 Chapters processed: {len(common_chapters)}")
        
        # Final verification
        self.stdout.write("\n🔍 Final verification:")
        for chapter_key, chapter_name in common_chapters:
            sl_count = Biology_SL_Questionbank.objects.filter(chapter=chapter_key).count()
            hl_count = Biology_HL_Questionbank.objects.filter(chapter=chapter_key).count()
            self.stdout.write(f"   {chapter_name}: SL={sl_count}, HL={hl_count}")

    def show_chapter_analysis(self):
        """
        Show detailed analysis of chapters and question counts
        """
        self.stdout.write(self.style.SUCCESS('🧬 Biology Question Bank Analysis'))
        self.stdout.write('=' * 50)
        
        common_chapters = self.get_common_chapters()
        
        self.stdout.write(f"📋 Common chapters between SL and HL ({len(common_chapters)}):")
        self.stdout.write(f"{'Chapter Name':<35} {'SL Count':<10} {'HL Count':<10}")
        self.stdout.write("-" * 55)
        
        total_sl = 0
        total_hl = 0
        
        for chapter_key, chapter_name in common_chapters:
            sl_count = Biology_SL_Questionbank.objects.filter(chapter=chapter_key).count()
            hl_count = Biology_HL_Questionbank.objects.filter(chapter=chapter_key).count()
            self.stdout.write(f"{chapter_name:<35} {sl_count:<10} {hl_count:<10}")
            total_sl += sl_count
            total_hl += hl_count
        
        self.stdout.write("-" * 55)
        self.stdout.write(f"{'TOTAL':<35} {total_sl:<10} {total_hl:<10}")
        
        # Show HL-only chapters
        sl_chapters = dict(Biology_SL_Questionbank.CHAPTERS)
        hl_chapters = dict(Biology_HL_Questionbank.CHAPTERS)
        
        hl_only_chapters = []
        for hl_chapter_key, hl_chapter_name in hl_chapters.items():
            if hl_chapter_key not in sl_chapters:
                hl_only_chapters.append((hl_chapter_key, hl_chapter_name))
        
        if hl_only_chapters:
            self.stdout.write(f"\n📖 HL-only chapters ({len(hl_only_chapters)}):")
            hl_only_total = 0
            for chapter_key, chapter_name in hl_only_chapters:
                hl_count = Biology_HL_Questionbank.objects.filter(chapter=chapter_key).count()
                self.stdout.write(f"   • {chapter_name}: {hl_count} questions")
                hl_only_total += hl_count
            self.stdout.write(f"   Total HL-only questions: {hl_only_total}")
        
        # Show SL-only chapters
        sl_only_chapters = []
        for sl_chapter_key, sl_chapter_name in sl_chapters.items():
            if sl_chapter_key not in hl_chapters:
                sl_only_chapters.append((sl_chapter_key, sl_chapter_name))
        
        if sl_only_chapters:
            self.stdout.write(f"\n📗 SL-only chapters ({len(sl_only_chapters)}):")
            sl_only_total = 0
            for chapter_key, chapter_name in sl_only_chapters:
                sl_count = Biology_SL_Questionbank.objects.filter(chapter=chapter_key).count()
                self.stdout.write(f"   • {chapter_name}: {sl_count} questions")
                sl_only_total += sl_count
            self.stdout.write(f"   Total SL-only questions: {sl_only_total}")
