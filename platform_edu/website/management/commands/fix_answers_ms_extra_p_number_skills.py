from django.core.management.base import BaseCommand
from website.models import Math_AI_SL_Questionbank
import re

class Command(BaseCommand):
    help = 'Fix <p class="answers-ms"><p> to <p class="answers-ms"> in Math AI SL number_skills chapter'

    def handle(self, *args, **kwargs):
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("Fixing Math AI SL - number_skills chapter")
        self.stdout.write(f"{'='*60}\n")
        
        # Pattern to find <p class="answers-ms"><p>
        pattern = r'<p class="answers-ms"><p>'
        
        # Get all questions from number_skills chapter
        questions = Math_AI_SL_Questionbank.objects.filter(chapter='number_skills')
        
        self.stdout.write(f"Total questions in number_skills: {questions.count()}")
        
        affected_questions = []
        fixed_count = 0
        
        for question in questions:
            if question.answer:
                # Check if this question has the pattern
                if re.search(pattern, question.answer):
                    affected_questions.append(question)
                    
                    # Show original (first 500 chars)
                    self.stdout.write(f"\n{'-'*60}")
                    self.stdout.write(f"Question ID: {question.id}")
                    self.stdout.write(f"Original (first 500 chars):")
                    self.stdout.write(question.answer[:500])
                    
                    # Fix: Replace <p class="answers-ms"><p> with <p class="answers-ms">
                    # Also need to remove the closing </p> that corresponds to the extra <p>
                    fixed_answer = question.answer
                    
                    # Replace <p class="answers-ms"><p> with <p class="answers-ms">
                    fixed_answer = re.sub(
                        r'<p class="answers-ms"><p>',
                        r'<p class="answers-ms">',
                        fixed_answer
                    )
                    
                    # Show fixed (first 500 chars)
                    self.stdout.write(f"\nFixed (first 500 chars):")
                    self.stdout.write(fixed_answer[:500])
                    
                    # Save the fixed answer
                    question.answer = fixed_answer
                    question.save()
                    fixed_count += 1
                    
                    self.stdout.write(self.style.SUCCESS(f"✓ Fixed question ID {question.id}"))
        
        self.stdout.write(f"\n{'='*60}")
        if fixed_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f"Successfully fixed {fixed_count} questions in number_skills chapter"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "No questions with the pattern found in number_skills chapter"
            ))
        self.stdout.write(f"{'='*60}\n")







