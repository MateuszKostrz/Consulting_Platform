"""
Management command to update Physics SL question types according to specific rules:
1. First 3 Paper 1A questions per chapter = 'free'
2. 50% of all questions = 'premium' (including all Paper 2 except 1)
3. Remaining questions (including 1 Paper 2) = 'registered'
"""

from django.core.management.base import BaseCommand
from website.models import Physics_SL_Questionbank
import random


class Command(BaseCommand):
    help = 'Updates Physics SL question types according to specified distribution rules'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Physics SL question type update...'))
        
        # Get all unique chapters
        chapters = Physics_SL_Questionbank.objects.values_list('chapter', flat=True).distinct()
        
        total_updated = 0
        summary = []
        
        for chapter in chapters:
            self.stdout.write(f'\n Processing chapter: {chapter}')
            
            # Get all questions for this chapter
            all_questions = list(Physics_SL_Questionbank.objects.filter(chapter=chapter))
            total_questions = len(all_questions)
            
            if total_questions == 0:
                self.stdout.write(self.style.WARNING(f'  No questions found for {chapter}'))
                continue
            
            # Separate questions by paper type
            paper1a_questions = [q for q in all_questions if q.paper == 'paper1A']
            paper1b_questions = [q for q in all_questions if q.paper == 'paper1B']
            paper2_questions = [q for q in all_questions if q.paper == 'paper2']
            
            # Count by paper type
            count_paper1a = len(paper1a_questions)
            count_paper1b = len(paper1b_questions)
            count_paper2 = len(paper2_questions)
            
            self.stdout.write(f'  Total questions: {total_questions}')
            self.stdout.write(f'    Paper 1A: {count_paper1a}')
            self.stdout.write(f'    Paper 1B: {count_paper1b}')
            self.stdout.write(f'    Paper 2: {count_paper2}')
            
            # STEP 1: Set first 3 Paper 1A questions to 'free'
            free_questions = []
            if count_paper1a >= 3:
                free_questions = paper1a_questions[:3]
                for q in free_questions:
                    q.type = 'free'
                    q.save()
            elif count_paper1a > 0:
                # If less than 3 Paper 1A questions, make all of them free
                free_questions = paper1a_questions
                for q in free_questions:
                    q.type = 'free'
                    q.save()
            
            # Remaining questions (excluding the 3 free ones)
            remaining_questions = [q for q in all_questions if q not in free_questions]
            remaining_count = len(remaining_questions)
            
            # STEP 2: Calculate how many questions should be premium (50% of total)
            target_premium_count = total_questions // 2
            
            # STEP 3: Handle Paper 2 questions - all but 1 should be premium
            premium_questions = []
            registered_questions = []
            
            if count_paper2 > 0:
                # Randomly select 1 Paper 2 question to be registered (not premium)
                paper2_registered = random.choice(paper2_questions)
                registered_questions.append(paper2_registered)
                
                # All other Paper 2 questions are premium
                paper2_premium = [q for q in paper2_questions if q != paper2_registered]
                premium_questions.extend(paper2_premium)
            
            # STEP 4: Calculate how many more premium questions we need from Paper 1A and 1B
            current_premium_count = len(premium_questions)
            needed_premium_count = target_premium_count - current_premium_count
            
            # Get Paper 1A and 1B questions that are not yet assigned (excluding free ones)
            available_for_premium = [q for q in remaining_questions 
                                    if q not in premium_questions 
                                    and q not in registered_questions
                                    and (q.paper == 'paper1A' or q.paper == 'paper1B')]
            
            # Randomly select additional questions to be premium
            if needed_premium_count > 0 and len(available_for_premium) > 0:
                # Don't exceed the number of available questions
                actual_premium_to_add = min(needed_premium_count, len(available_for_premium))
                additional_premium = random.sample(available_for_premium, actual_premium_to_add)
                premium_questions.extend(additional_premium)
            
            # STEP 5: All remaining questions are 'registered'
            for q in remaining_questions:
                if q not in premium_questions and q not in registered_questions:
                    registered_questions.append(q)
            
            # STEP 6: Save all premium and registered questions
            for q in premium_questions:
                q.type = 'premium'
                q.save()
            
            for q in registered_questions:
                q.type = 'registered'
                q.save()
            
            # Count and display results
            count_free = len(free_questions)
            count_premium = len(premium_questions)
            count_registered = len(registered_questions)
            
            self.stdout.write(self.style.SUCCESS(f'  Updated {chapter}:'))
            self.stdout.write(f'    Free: {count_free} questions')
            self.stdout.write(f'    Premium: {count_premium} questions ({count_premium/total_questions*100:.1f}%)')
            self.stdout.write(f'    Registered: {count_registered} questions')
            
            # Verify Paper 2 distribution
            paper2_premium_count = len([q for q in paper2_questions if q.type == 'premium'])
            paper2_registered_count = len([q for q in paper2_questions if q.type == 'registered'])
            paper2_free_count = len([q for q in paper2_questions if q.type == 'free'])
            
            if count_paper2 > 0:
                self.stdout.write(f'    Paper 2 breakdown:')
                self.stdout.write(f'      Premium: {paper2_premium_count}')
                self.stdout.write(f'      Registered: {paper2_registered_count}')
                self.stdout.write(f'      Free: {paper2_free_count}')
            
            total_updated += total_questions
            
            summary.append({
                'chapter': chapter,
                'total': total_questions,
                'free': count_free,
                'premium': count_premium,
                'registered': count_registered
            })
        
        # Display final summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('='*70)
        
        total_free = sum(s['free'] for s in summary)
        total_premium = sum(s['premium'] for s in summary)
        total_registered = sum(s['registered'] for s in summary)
        grand_total = sum(s['total'] for s in summary)
        
        self.stdout.write(f'\nTotal questions processed: {grand_total}')
        self.stdout.write(f'  Free: {total_free} ({total_free/grand_total*100:.1f}%)')
        self.stdout.write(f'  Premium: {total_premium} ({total_premium/grand_total*100:.1f}%)')
        self.stdout.write(f'  Registered: {total_registered} ({total_registered/grand_total*100:.1f}%)')
        
        self.stdout.write('\n' + self.style.SUCCESS('Physics SL question types updated successfully!'))






