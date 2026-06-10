from django.core.management.base import BaseCommand
from website.models import Math_AI_SL_Questionbank
import re

class Command(BaseCommand):
    help = 'Fix nested <p class="answers-ms"> tags in all Math AI SL questions'

    def handle(self, *args, **kwargs):
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("Fixing all Math AI SL questions")
        self.stdout.write(f"{'='*60}\n")
        
        # Get all questions from Math AI SL
        questions = Math_AI_SL_Questionbank.objects.all()
        
        self.stdout.write(f"Total questions in Math AI SL: {questions.count()}")
        
        fixed_count = 0
        chapters_fixed = {}
        
        for question in questions:
            if question.answer:
                original_answer = question.answer
                modified = False
                
                # Step 1: Fix nested <p class="answers-ms"> tags
                # Replace multiple consecutive <p class="answers-ms"> with just one
                if re.search(r'(<p class="answers-ms">){2,}', original_answer):
                    question.answer = re.sub(
                        r'(<p class="answers-ms">){2,}',
                        r'<p class="answers-ms">',
                        question.answer
                    )
                    modified = True
                
                # Step 2: Fix <p class="answers-ms"><p> pattern
                if re.search(r'<p class="answers-ms"><p>', question.answer):
                    question.answer = re.sub(
                        r'<p class="answers-ms"><p>',
                        r'<p class="answers-ms">',
                        question.answer
                    )
                    modified = True
                
                if modified:
                    # Track which chapters were fixed
                    chapter = question.chapter if hasattr(question, 'chapter') else 'Unknown'
                    if chapter not in chapters_fixed:
                        chapters_fixed[chapter] = 0
                    chapters_fixed[chapter] += 1
                    
                    # Show progress every 10 questions
                    if fixed_count % 10 == 0:
                        self.stdout.write(f"Processing... Fixed {fixed_count} questions so far")
                    
                    # Save the fixed answer
                    question.save()
                    fixed_count += 1
        
        self.stdout.write(f"\n{'='*60}")
        if fixed_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f"Successfully fixed {fixed_count} questions in Math AI SL"
            ))
            self.stdout.write(f"\nBreakdown by chapter:")
            for chapter, count in sorted(chapters_fixed.items()):
                self.stdout.write(f"  - {chapter}: {count} questions")
        else:
            self.stdout.write(self.style.SUCCESS(
                "No questions with nested tags found in Math AI SL"
            ))
        self.stdout.write(f"{'='*60}\n")







