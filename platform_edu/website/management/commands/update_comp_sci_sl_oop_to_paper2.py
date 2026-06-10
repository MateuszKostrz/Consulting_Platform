"""
Management command to update Computer Science SL OOP questions to Paper 2.

This script will change all OOP chapter questions to paper='paper2'
"""

from django.core.management.base import BaseCommand
from website.models import Comp_Sci_SL_Questionbank


class Command(BaseCommand):
    help = 'Updates Computer Science SL OOP chapter questions to Paper 2'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Computer Science SL OOP → Paper 2 conversion...'))
        
        # OOP chapter
        chapter = 'oop'
        
        self.stdout.write(f'\nConverting OOP chapter to Paper 2...\n')
        
        # Get all questions for OOP chapter
        questions = Comp_Sci_SL_Questionbank.objects.filter(chapter=chapter)
        total_questions = questions.count()
        
        if total_questions == 0:
            self.stdout.write(self.style.WARNING('✗ OOP: No questions found'))
            return
        
        # Count questions by current paper type
        paper1_before = questions.filter(paper='paper1').count()
        paper2_before = questions.filter(paper='paper2').count()
        practice_before = questions.filter(paper='practice').count()
        
        self.stdout.write(f'OOP Chapter:')
        self.stdout.write(f'  Total questions: {total_questions}')
        self.stdout.write(f'  Current distribution:')
        self.stdout.write(f'    Paper 1: {paper1_before}')
        self.stdout.write(f'    Paper 2: {paper2_before}')
        self.stdout.write(f'    Practice: {practice_before}')
        
        # Update all questions to Paper 2
        updated_count = questions.update(paper='paper2')
        
        # Verify the update
        paper1_after = questions.filter(paper='paper1').count()
        paper2_after = questions.filter(paper='paper2').count()
        practice_after = questions.filter(paper='practice').count()
        
        self.stdout.write(f'  After conversion:')
        self.stdout.write(f'    Paper 1: {paper1_after}')
        self.stdout.write(f'    Paper 2: {paper2_after}')
        self.stdout.write(f'    Practice: {practice_after}')
        
        if paper2_after == total_questions and paper1_after == 0 and practice_after == 0:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Successfully converted all {total_questions} OOP questions to Paper 2'))
        else:
            self.stdout.write(self.style.WARNING(f'  ⚠️ Warning: Conversion may have issues'))
        
        # Display final summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('SUMMARY - Computer Science SL OOP Chapter'))
        self.stdout.write('='*70)
        
        self.stdout.write(f'\nTotal OOP questions: {total_questions}')
        self.stdout.write(f'\nBefore conversion:')
        self.stdout.write(f'  Paper 1: {paper1_before} ({paper1_before/total_questions*100:.1f}%)')
        self.stdout.write(f'  Paper 2: {paper2_before} ({paper2_before/total_questions*100:.1f}%)')
        self.stdout.write(f'  Practice: {practice_before} ({practice_before/total_questions*100:.1f}%)')
        
        self.stdout.write(f'\nAfter conversion:')
        self.stdout.write(f'  Paper 2: {paper2_after} ({paper2_after/total_questions*100:.1f}%)')
        
        # Check if conversion was successful
        if paper2_after == total_questions:
            converted = total_questions - paper2_before
            self.stdout.write(self.style.SUCCESS(f'\n✓ All {total_questions} OOP questions are now Paper 2! (converted {converted})'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠️ Warning: Not all questions were converted'))
        
        self.stdout.write('\n' + self.style.SUCCESS('Computer Science SL OOP chapter conversion completed!'))








