from django.core.management.base import BaseCommand
from website.models import Math_AA_SL_Questionbank, Math_AA_HL_Questionbank


class Command(BaseCommand):
    help = 'Check which SL questions will not be copied to HL'

    def handle(self, *args, **options):
        # Get chapter choices
        sl_chapters = dict(Math_AA_SL_Questionbank.CHAPTERS)
        hl_chapters = dict(Math_AA_HL_Questionbank.CHAPTERS)

        # Define mappings
        chapter_mappings = {
            'integration': 'integral_calculus',
            'differentiation': 'differential_calculus'
        }

        # Find overlapping chapters
        overlapping_chapters = set(sl_chapters.keys()) & set(hl_chapters.keys())

        # Add mapped chapters
        for sl_chapter, hl_chapter in chapter_mappings.items():
            if sl_chapter in sl_chapters and hl_chapter in hl_chapters:
                overlapping_chapters.add(sl_chapter)

        self.stdout.write(f"Total SL chapters: {len(sl_chapters)}")
        self.stdout.write(f"Overlapping chapters: {len(overlapping_chapters)}")
        self.stdout.write(f"SL chapters that will be copied: {sorted(overlapping_chapters)}")

        # Find non-overlapping chapters
        non_overlapping = set(sl_chapters.keys()) - overlapping_chapters
        self.stdout.write(f"\nSL chapters that WON'T be copied: {non_overlapping}")

        # Check questions in non-overlapping chapters
        if non_overlapping:
            for chapter in non_overlapping:
                count = Math_AA_SL_Questionbank.objects.filter(chapter=chapter).count()
                self.stdout.write(f"  {chapter}: {count} questions")
                
            # Show the actual questions
            self.stdout.write(f"\nQuestions that won't be copied:")
            for chapter in non_overlapping:
                questions = Math_AA_SL_Questionbank.objects.filter(chapter=chapter)
                for i, q in enumerate(questions, 1):
                    self.stdout.write(f"  {chapter} #{i}: {q.question[:100]}...")

        # Double-check counts
        total_sl = Math_AA_SL_Questionbank.objects.count()
        overlapping_count = Math_AA_SL_Questionbank.objects.filter(chapter__in=overlapping_chapters).count()
        non_overlapping_count = Math_AA_SL_Questionbank.objects.filter(chapter__in=non_overlapping).count()

        self.stdout.write(f"\nSanity check:")
        self.stdout.write(f"Total SL questions: {total_sl}")
        self.stdout.write(f"Overlapping questions: {overlapping_count}")
        self.stdout.write(f"Non-overlapping questions: {non_overlapping_count}")
        self.stdout.write(f"Sum: {overlapping_count + non_overlapping_count} (should equal {total_sl})") 