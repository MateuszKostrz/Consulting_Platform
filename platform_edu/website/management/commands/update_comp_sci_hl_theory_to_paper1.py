"""
Management command to update ALL Computer Science HL Theory questions to Paper 1.

Theory chapters (6 total):
- System Fundamentals (SL + HL)
- Computer Organisation (SL + HL)
- Networks (SL + HL)
- Computational Thinking (SL + HL)
- Resource Management (HL only)
- Abstract Data Structures (HL only)

This script will change all questions in these Theory chapters to paper='paper1'
"""

from django.core.management.base import BaseCommand
from website.models import Comp_Sci_HL_Questionbank


class Command(BaseCommand):
    help = 'Updates ALL Computer Science HL Theory chapter questions to Paper 1'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Computer Science HL Theory → Paper 1 conversion...'))
        
        # Define ALL Theory chapters (including SL chapters that are also in HL)
        all_theory_chapters = [
            'system_fundamentals',
            'computer_organisation',
            'networks',
            'computational_thinking',
            'resource_management',
            'abstract_data_structures'
        ]
        
        self.stdout.write(f'\nALL Theory chapters to process:')
        self.stdout.write(f'  • System Fundamentals')
        self.stdout.write(f'  • Computer Organisation')
        self.stdout.write(f'  • Networks')
        self.stdout.write(f'  • Computational Thinking')
        self.stdout.write(f'  • Resource Management')
        self.stdout.write(f'  • Abstract Data Structures')
        
        self.stdout.write('')  # Empty line
        
        total_updated = 0
        summary = []
        
        for chapter in all_theory_chapters:
            # Get all questions for this chapter
            questions = Comp_Sci_HL_Questionbank.objects.filter(chapter=chapter)
            total_questions = questions.count()
            
            if total_questions == 0:
                chapter_name = chapter.replace('_', ' ').title()
                self.stdout.write(self.style.WARNING(f'✗ {chapter_name}: No questions found'))
                continue
            
            # Count questions by current paper type
            paper1_before = questions.filter(paper='paper1').count()
            paper2_before = questions.filter(paper='paper2').count()
            
            chapter_name = chapter.replace('_', ' ').title()
            self.stdout.write(f'\n{chapter_name}:')
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
                'chapter_name': chapter_name,
                'total': total_questions,
                'paper1_before': paper1_before,
                'paper2_before': paper2_before,
                'paper1_after': paper1_after,
                'paper2_after': paper2_after
            })
        
        # Display final summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('SUMMARY - Computer Science HL Theory Chapters (ALL)'))
        self.stdout.write('='*70)
        
        if summary:
            grand_total = sum(s['total'] for s in summary)
            total_paper1_before = sum(s['paper1_before'] for s in summary)
            total_paper2_before = sum(s['paper2_before'] for s in summary)
            total_paper1_after = sum(s['paper1_after'] for s in summary)
            total_paper2_after = sum(s['paper2_after'] for s in summary)
            
            self.stdout.write(f'\nTotal questions in ALL Theory chapters: {grand_total}')
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
                converted = s['total'] - s['paper1_before']
                self.stdout.write(f"  {s['chapter_name']}: {s['total']} questions (converted {converted})")
            
            self.stdout.write('\n' + self.style.SUCCESS('Computer Science HL Theory chapter conversion completed!'))
        else:
            self.stdout.write(self.style.WARNING('No chapters were processed.'))

