from django.core.management.base import BaseCommand
from website.models import Math_AI_SL_Questionbank
import re

class Command(BaseCommand):
    help = 'Fix nested <p class="answers-ms"> tags in Math AI SL number_skills chapter'

    def handle(self, *args, **kwargs):
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("Fixing Math AI SL - number_skills chapter")
        self.stdout.write(f"{'='*60}\n")
        
        # Pattern to find nested <p class="answers-ms"> tags
        nested_pattern = r'(<p class="answers-ms">){2,}'
        
        # Get all questions from number_skills chapter
        questions = Math_AI_SL_Questionbank.objects.filter(chapter='number_skills')
        
        self.stdout.write(f"Total questions in number_skills: {questions.count()}")
        
        affected_questions = []
        fixed_count = 0
        
        for question in questions:
            if question.answer:
                # Check if this question has nested tags
                if re.search(nested_pattern, question.answer):
                    affected_questions.append(question)
                    
                    # Show original (first 500 chars)
                    self.stdout.write(f"\n{'-'*60}")
                    self.stdout.write(f"Question ID: {question.id}")
                    self.stdout.write(f"Original (first 500 chars):")
                    self.stdout.write(question.answer[:500])
                    
                    # Fix: Replace multiple consecutive <p class="answers-ms"> with just one
                    fixed_answer = re.sub(
                        r'(<p class="answers-ms">){2,}',
                        r'<p class="answers-ms">',
                        question.answer
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
                "No questions with nested tags found in number_skills chapter"
            ))
        self.stdout.write(f"{'='*60}\n")







