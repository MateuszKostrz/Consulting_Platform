from django.core.management.base import BaseCommand
from website.models import Math_AA_SL_Questionbank


class Command(BaseCommand):
    help = 'Find SL questions with invalid chapter values'

    def handle(self, *args, **options):
        # Get valid chapter choices
        valid_chapters = [choice[0] for choice in Math_AA_SL_Questionbank.CHAPTERS]
        
        self.stdout.write(f"Valid SL chapters: {valid_chapters}")
        self.stdout.write(f"Total valid chapters: {len(valid_chapters)}")
        
        # Find all unique chapter values in the database
        all_chapters = Math_AA_SL_Questionbank.objects.values_list('chapter', flat=True).distinct()
        self.stdout.write(f"\nAll chapter values in database: {sorted(all_chapters)}")
        self.stdout.write(f"Total unique chapters in DB: {len(all_chapters)}")
        
        # Find invalid chapters
        invalid_chapters = set(all_chapters) - set(valid_chapters)
        self.stdout.write(f"\nInvalid chapter values: {invalid_chapters}")
        
        if invalid_chapters:
            self.stdout.write(f"\nQuestions with invalid chapters:")
            for invalid_chapter in invalid_chapters:
                questions = Math_AA_SL_Questionbank.objects.filter(chapter=invalid_chapter)
                count = questions.count()
                self.stdout.write(f"\n'{invalid_chapter}': {count} questions")
                
                for i, q in enumerate(questions, 1):
                    self.stdout.write(f"  #{i}: {q.question[:100]}...")
        else:
            self.stdout.write("No invalid chapters found - all questions have valid chapter values") 