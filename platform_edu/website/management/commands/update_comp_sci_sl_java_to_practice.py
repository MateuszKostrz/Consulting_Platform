"""
Management command to update Computer Science SL Java questions to Practice paper.

Java Intro chapters (5):
- Variables and Input
- If Statements
- Loops
- Arrays
- Methods

Java Intermediate chapters (1):
- Constructors

Note: OOP is NOT included (stays as Paper 2)

This script will change all questions in these 6 chapters to paper='practice'
"""

from django.core.management.base import BaseCommand
from website.models import Comp_Sci_SL_Questionbank


class Command(BaseCommand):
    help = 'Updates Computer Science SL Java chapter questions to Practice paper (excluding OOP)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Computer Science SL Java → Practice conversion...'))
        
        # Define Java chapters (Intro + Intermediate, EXCLUDING OOP)
        java_chapters = [
            # Java Intro
            'variables_input',
            'if_statements',
            'loops',
            'arrays',
            'methods',
            # Java Intermediate
            'constructors'
        ]
        
        self.stdout.write(f'\nJava chapters to process:')
        self.stdout.write(f'\nJava Intro (5 chapters):')
        self.stdout.write(f'  • Variables and Input')
        self.stdout.write(f'  • If Statements')
        self.stdout.write(f'  • Loops')
        self.stdout.write(f'  • Arrays')
        self.stdout.write(f'  • Methods')
        self.stdout.write(f'\nJava Intermediate (1 chapter):')
        self.stdout.write(f'  • Constructors')
        self.stdout.write(f'\nExcluded (stays as Paper 2):')
        self.stdout.write(f'  • OOP\n')
        
        total_updated = 0
        summary = []
        
        for chapter in java_chapters:
            # Get all questions for this chapter
            questions = Comp_Sci_SL_Questionbank.objects.filter(chapter=chapter)
            total_questions = questions.count()
            
            if total_questions == 0:
                chapter_name = chapter.replace('_', ' ').title()
                self.stdout.write(self.style.WARNING(f'✗ {chapter_name}: No questions found'))
                continue
            
            # Count questions by current paper type
            paper1_before = questions.filter(paper='paper1').count()
            paper2_before = questions.filter(paper='paper2').count()
            practice_before = questions.filter(paper='practice').count()
            
            chapter_name = chapter.replace('_', ' ').title()
            self.stdout.write(f'{chapter_name}:')
            self.stdout.write(f'  Total questions: {total_questions}')
            self.stdout.write(f'  Current distribution:')
            self.stdout.write(f'    Paper 1: {paper1_before}')
            self.stdout.write(f'    Paper 2: {paper2_before}')
            self.stdout.write(f'    Practice: {practice_before}')
            
            # Update all questions to Practice
            updated_count = questions.update(paper='practice')
            
            # Verify the update
            paper1_after = questions.filter(paper='paper1').count()
            paper2_after = questions.filter(paper='paper2').count()
            practice_after = questions.filter(paper='practice').count()
            
            self.stdout.write(f'  After conversion:')
            self.stdout.write(f'    Paper 1: {paper1_after}')
            self.stdout.write(f'    Paper 2: {paper2_after}')
            self.stdout.write(f'    Practice: {practice_after}')
            
            if practice_after == total_questions and paper1_after == 0 and paper2_after == 0:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Successfully converted all {total_questions} questions to Practice'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Warning: Conversion may have issues'))
            
            self.stdout.write('')  # Empty line for readability
            
            total_updated += updated_count
            
            summary.append({
                'chapter': chapter,
                'chapter_name': chapter_name,
                'total': total_questions,
                'paper1_before': paper1_before,
                'paper2_before': paper2_before,
                'practice_before': practice_before,
                'practice_after': practice_after
            })
        
        # Display final summary
        self.stdout.write('='*70)
        self.stdout.write(self.style.SUCCESS('SUMMARY - Computer Science SL Java Chapters'))
        self.stdout.write('='*70)
        
        if summary:
            grand_total = sum(s['total'] for s in summary)
            total_paper1_before = sum(s['paper1_before'] for s in summary)
            total_paper2_before = sum(s['paper2_before'] for s in summary)
            total_practice_before = sum(s['practice_before'] for s in summary)
            total_practice_after = sum(s['practice_after'] for s in summary)
            
            self.stdout.write(f'\nTotal questions in Java chapters: {grand_total}')
            self.stdout.write(f'\nBefore conversion:')
            self.stdout.write(f'  Paper 1: {total_paper1_before} ({total_paper1_before/grand_total*100:.1f}%)')
            self.stdout.write(f'  Paper 2: {total_paper2_before} ({total_paper2_before/grand_total*100:.1f}%)')
            self.stdout.write(f'  Practice: {total_practice_before} ({total_practice_before/grand_total*100:.1f}%)')
            
            self.stdout.write(f'\nAfter conversion:')
            self.stdout.write(f'  Practice: {total_practice_after} ({total_practice_after/grand_total*100:.1f}%)')
            
            # Check if conversion was successful
            if total_practice_after == grand_total:
                self.stdout.write(self.style.SUCCESS(f'\n✓ All {grand_total} Java questions are now Practice paper!'))
            else:
                self.stdout.write(self.style.WARNING(f'\n⚠️ Warning: Not all questions were converted'))
            
            # Show breakdown by section
            self.stdout.write(f'\nBreakdown by section:')
            
            java_intro_chapters = ['variables_input', 'if_statements', 'loops', 'arrays', 'methods']
            java_intermediate_chapters = ['constructors']
            
            intro_total = sum(s['total'] for s in summary if s['chapter'] in java_intro_chapters)
            intermediate_total = sum(s['total'] for s in summary if s['chapter'] in java_intermediate_chapters)
            
            self.stdout.write(f'  Java Intro: {intro_total} questions')
            for s in summary:
                if s['chapter'] in java_intro_chapters:
                    converted = s['total'] - s['practice_before']
                    self.stdout.write(f"    {s['chapter_name']}: {s['total']} questions (converted {converted})")
            
            self.stdout.write(f'  Java Intermediate: {intermediate_total} questions')
            for s in summary:
                if s['chapter'] in java_intermediate_chapters:
                    converted = s['total'] - s['practice_before']
                    self.stdout.write(f"    {s['chapter_name']}: {s['total']} questions (converted {converted})")
            
            self.stdout.write('\n' + self.style.SUCCESS('Computer Science SL Java chapter conversion completed!'))
        else:
            self.stdout.write(self.style.WARNING('No chapters were processed.'))

