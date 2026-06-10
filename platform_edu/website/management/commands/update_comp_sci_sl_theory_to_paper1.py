"""
Management command to update all Computer Science SL Theory questions to Paper 1.

Theory chapters (4 total):
- System Fundamentals
- Computer Organisation
- Networks
- Computational Thinking

This script will change all questions in these chapters to paper='paper1'
"""

from django.core.management.base import BaseCommand
from website.models import Comp_Sci_SL_Questionbank


class Command(BaseCommand):
    help = 'Updates all Computer Science SL Theory chapter questions to Paper 1'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Computer Science SL Theory → Paper 1 conversion...'))
        
        # Define Theory chapters
        theory_chapters = [
            'system_fundamentals',
            'computer_organisation',
            'networks',
            'computational_thinking'
        ]
        
        self.stdout.write(f'\nTheory chapters to process:')
        self.stdout.write(f'  • System Fundamentals')
        self.stdout.write(f'  • Computer Organisation')
        self.stdout.write(f'  • Networks')
        self.stdout.write(f'  • Computational Thinking\n')
        
        total_updated = 0
        summary = []
        
        for chapter in theory_chapters:
            # Get all questions for this chapter
            questions = Comp_Sci_SL_Questionbank.objects.filter(chapter=chapter)
            total_questions = questions.count()
            
            if total_questions == 0:
                self.stdout.write(self.style.WARNING(f'✗ {chapter}: No questions found'))
                continue
            
            # Count questions by current paper type
            paper1_before = questions.filter(paper='paper1').count()
            paper2_before = questions.filter(paper='paper2').count()
            
            self.stdout.write(f'\n{chapter}:')
            self.stdout.write(f'  Total questions: {total_questions}')
            self.stdout.write(f'  Current distribution:')
            self.stdout.write(f'    Paper 1: {paper1_before}')
            self.stdout.write(f'    Paper 2: {paper2_before}')
            
            # Update all questions to Paper 1
            updated_count = questions.update(paper='paper1')
            
            # Verify the update
            paper1_after = questions.filter(paper='paper1').count()
            paper2_after = questions.filter(paper='paper2').count()
            
            self.stdout.write(f'  After conversion:')
            self.stdout.write(f'    Paper 1: {paper1_after}')
            self.stdout.write(f'    Paper 2: {paper2_after}')
            
            if paper1_after == total_questions and paper2_after == 0:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Successfully converted all {total_questions} questions to Paper 1'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Warning: Conversion may have issues'))
            
            total_updated += updated_count
            
            summary.append({
                'chapter': chapter,
                'total': total_questions,
                'paper1_before': paper1_before,
                'paper2_before': paper2_before,
                'paper1_after': paper1_after,
                'paper2_after': paper2_after
            })
        
        # Display final summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('SUMMARY - Computer Science SL Theory Chapters'))
        self.stdout.write('='*70)
        
        if summary:
            grand_total = sum(s['total'] for s in summary)
            total_paper1_before = sum(s['paper1_before'] for s in summary)
            total_paper2_before = sum(s['paper2_before'] for s in summary)
            total_paper1_after = sum(s['paper1_after'] for s in summary)
            total_paper2_after = sum(s['paper2_after'] for s in summary)
            
            self.stdout.write(f'\nTotal questions in Theory chapters: {grand_total}')
            self.stdout.write(f'\nBefore conversion:')
            self.stdout.write(f'  Paper 1: {total_paper1_before} ({total_paper1_before/grand_total*100:.1f}%)')
            self.stdout.write(f'  Paper 2: {total_paper2_before} ({total_paper2_before/grand_total*100:.1f}%)')
            
            self.stdout.write(f'\nAfter conversion:')
            self.stdout.write(f'  Paper 1: {total_paper1_after} ({total_paper1_after/grand_total*100:.1f}%)')
            self.stdout.write(f'  Paper 2: {total_paper2_after} ({total_paper2_after/grand_total*100:.1f}%)')
            
            # Check if conversion was successful
            if total_paper1_after == grand_total and total_paper2_after == 0:
                self.stdout.write(self.style.SUCCESS(f'\n✓ All {grand_total} Theory questions are now Paper 1!'))
            else:
                self.stdout.write(self.style.WARNING(f'\n⚠️ Warning: Not all questions were converted'))
            
            # Show breakdown by chapter
            self.stdout.write(f'\nBreakdown by chapter:')
            for s in summary:
                chapter_name = s['chapter'].replace('_', ' ').title()
                converted = s['total'] - s['paper1_before']
                self.stdout.write(f"  {chapter_name}: {s['total']} questions (converted {converted})")
            
            self.stdout.write('\n' + self.style.SUCCESS('Computer Science SL Theory chapter conversion completed!'))
        else:
            self.stdout.write(self.style.WARNING('No chapters were processed.'))








