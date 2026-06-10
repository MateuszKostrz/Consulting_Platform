from django.core.management.base import BaseCommand
from website.models import Math_AI_SL_Questionbank
import re

class Command(BaseCommand):
    help = 'Fix nested <p class="answers-ms"> tags in Math AI SL seq_series chapter'

    def handle(self, *args, **kwargs):
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("Fixing Math AI SL - seq_series chapter")
        self.stdout.write(f"{'='*60}\n")
        
        # Get all questions from seq_series chapter
        questions = Math_AI_SL_Questionbank.objects.filter(chapter='seq_series')
        
        self.stdout.write(f"Total questions in seq_series: {questions.count()}")
        
        fixed_count = 0
        
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
                    # Show original (first 500 chars)
                    self.stdout.write(f"\n{'-'*60}")
                    self.stdout.write(f"Question ID: {question.id}")
                    self.stdout.write(f"Original (first 500 chars):")
                    self.stdout.write(original_answer[:500])
                    
                    # Show fixed (first 500 chars)
                    self.stdout.write(f"\nFixed (first 500 chars):")
                    self.stdout.write(question.answer[:500])
                    
                    # Save the fixed answer
                    question.save()
                    fixed_count += 1
                    
                    self.stdout.write(self.style.SUCCESS(f"✓ Fixed question ID {question.id}"))
        
        self.stdout.write(f"\n{'='*60}")
        if fixed_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f"Successfully fixed {fixed_count} questions in seq_series chapter"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "No questions with nested tags found in seq_series chapter"
            ))
        self.stdout.write(f"{'='*60}\n")







