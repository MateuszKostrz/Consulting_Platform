from django.core.management.base import BaseCommand
from website.models import (
    Math_AI_SL_Questionbank, Math_AI_HL_Questionbank,
    Math_AA_SL_Questionbank, Math_AA_HL_Questionbank,
    Biology_SL_Questionbank, Biology_HL_Questionbank,
    Physics_SL_Questionbank, Physics_HL_Questionbank,
    Comp_Sci_SL_Questionbank, Comp_Sci_HL_Questionbank
)
import re

class Command(BaseCommand):
    help = 'Identify questions with nested <p class="answers-ms"> tags'

    def handle(self, *args, **kwargs):
        # Define all questionbank models
        models = {
            'Math AI SL': Math_AI_SL_Questionbank,
            'Math AI HL': Math_AI_HL_Questionbank,
            'Math AA SL': Math_AA_SL_Questionbank,
            'Math AA HL': Math_AA_HL_Questionbank,
            'Biology SL': Biology_SL_Questionbank,
            'Biology HL': Biology_HL_Questionbank,
            'Physics SL': Physics_SL_Questionbank,
            'Physics HL': Physics_HL_Questionbank,
            'Computer Science SL': Comp_Sci_SL_Questionbank,
            'Computer Science HL': Comp_Sci_HL_Questionbank,
        }
        
        # Pattern to find nested <p class="answers-ms"> tags
        # This looks for multiple consecutive <p class="answers-ms"> without closing tags
        nested_pattern = r'(<p class="answers-ms">){2,}'
        
        total_affected = 0
        
        for subject_name, model in models.items():
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Checking {subject_name}...")
            self.stdout.write(f"{'='*60}")
            
            affected_questions = []
            
            # Check all questions in this model
            all_questions = model.objects.all()
            
            for question in all_questions:
                # Check if answer field exists and has content
                if hasattr(question, 'answer') and question.answer:
                    # Check for nested pattern
                    matches = re.findall(nested_pattern, question.answer)
                    if matches:
                        # Count how many nested tags
                        max_nested = max(len(re.findall(r'<p class="answers-ms">', match_group)) 
                                       for match_group in re.findall(nested_pattern, question.answer))
                        
                        affected_questions.append({
                            'id': question.id,
                            'question_number': question.question_number if hasattr(question, 'question_number') else 'N/A',
                            'chapter': question.chapter if hasattr(question, 'chapter') else 'N/A',
                            'nested_count': max_nested,
                        })
            
            if affected_questions:
                self.stdout.write(self.style.WARNING(
                    f"\nFound {len(affected_questions)} questions with nested <p class=\"answers-ms\"> tags:"
                ))
                
                for q in affected_questions[:10]:  # Show first 10
                    self.stdout.write(
                        f"  - ID: {q['id']}, Question: {q['question_number']}, "
                        f"Chapter: {q['chapter']}, Nested depth: {q['nested_count']}"
                    )
                
                if len(affected_questions) > 10:
                    self.stdout.write(f"  ... and {len(affected_questions) - 10} more")
                
                total_affected += len(affected_questions)
            else:
                self.stdout.write(self.style.SUCCESS(f"No issues found in {subject_name}"))
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.WARNING(
            f"\nTOTAL: {total_affected} questions affected across all subjects"
        ))
        self.stdout.write(f"{'='*60}\n")







