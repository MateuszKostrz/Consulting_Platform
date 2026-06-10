"""
Django management command to automatically distribute access tiers for ALL chapters in a subject.

Usage:
    python manage.py auto_distribute_all_chapters
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from website.models import (
    Physics_SL_Questionbank,
    Physics_HL_Questionbank,
)

# ======================== CONFIGURATION ========================
# Choose which subjects to process (set to True to process)
PROCESS_PHYSICS_SL = True
PROCESS_PHYSICS_HL = True
# ===============================================================


class Command(BaseCommand):
    help = 'Automatically distribute access tiers for ALL chapters in a subject'
    
    # Map subject names to their models and chapters
    SUBJECT_CONFIG = {
        'physics_sl': {
            'model': Physics_SL_Questionbank,
            'chapters': [
                'kinematics',
                'forces_and_momentum',
                'work_energy_power',
                'thermal_energy',
                'greenhouse_effect',
                'ideal_gas_model',
                'electric_circuits',
                'simple_harmonic_motion',
                'wave_model',
                'wave_phenomena',
                'standing_waves',
                'doppler_effect',
                'gravitational_fields',
                'electric_magnetic_fields',
                'motion_in_fields',
                'structure_atom',
                'radioactive_decay',
                'fission',
                'fusion_and_stars',
            ]
        },
        'physics_hl': {
            'model': Physics_HL_Questionbank,
            'chapters': [
                'kinematics',
                'forces_and_momentum',
                'work_energy_power',
                'thermal_energy',
                'greenhouse_effect',
                'ideal_gas_model',
                'electric_circuits',
                'simple_harmonic_motion',
                'wave_model',
                'wave_phenomena',
                'standing_waves',
                'doppler_effect',
                'gravitational_fields',
                'electric_magnetic_fields',
                'motion_in_fields',
                'structure_atom',
                'radioactive_decay',
                'fission',
                'fusion_and_stars',
            ]
        }
    }
    
    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('AUTO DISTRIBUTE ALL CHAPTERS'))
        self.stdout.write('=' * 70)
        
        # Determine which subjects to process
        subjects_to_process = []
        if PROCESS_PHYSICS_SL:
            subjects_to_process.append('physics_sl')
        if PROCESS_PHYSICS_HL:
            subjects_to_process.append('physics_hl')
        
        if not subjects_to_process:
            self.stdout.write(self.style.ERROR('\n❌ No subjects selected. Set PROCESS_PHYSICS_SL or PROCESS_PHYSICS_HL to True.'))
            return
        
        self.stdout.write(f'\n📚 Subjects to process: {", ".join([s.upper() for s in subjects_to_process])}')
        
        # Count total chapters
        total_chapters_count = sum(len(self.SUBJECT_CONFIG[s]['chapters']) for s in subjects_to_process)
        self.stdout.write(f'📖 Total chapters: {total_chapters_count}')
        self.stdout.write('\n' + '=' * 70)
        
        # Ask for confirmation upfront
        confirm = input(f'\n⚠️  Process {len(subjects_to_process)} subject(s) with {total_chapters_count} chapters total? (yes/no): ')
        
        if confirm.lower() not in ['yes', 'y']:
            self.stdout.write(self.style.WARNING('\n❌ Operation cancelled.'))
            return
        
        # Track overall statistics across ALL subjects
        grand_total_chapters = 0
        grand_total_free = 0
        grand_total_registered = 0
        grand_total_premium = 0
        
        # Process each subject
        for SUBJECT in subjects_to_process:
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write('=' * 70)
            self.stdout.write(self.style.SUCCESS(f'🔬 PROCESSING SUBJECT: {SUBJECT.upper()}'))
            self.stdout.write('=' * 70)
            self.stdout.write('=' * 70)
            
            config = self.SUBJECT_CONFIG[SUBJECT]
            model = config['model']
            chapters = config['chapters']
            
            # Track statistics per subject
            total_chapters_processed = 0
            total_free = 0
            total_registered = 0
            total_premium = 0
            chapters_with_no_questions = []
            
            # Process each chapter
        for chapter in chapters:
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(f'📖 Processing: {self.style.WARNING(chapter.upper())}')
            self.stdout.write('-' * 70)
            
            # Find all questions in this chapter
            query = Q(chapter=chapter)
            if hasattr(model, 'chapter2'):
                field_names = [f.name for f in model._meta.get_fields()]
                if 'chapter2' in field_names:
                    query |= Q(chapter2=chapter)
                if 'chapter3' in field_names:
                    query |= Q(chapter3=chapter)
            
            questions = model.objects.filter(query).order_by('id')
            total_count = questions.count()
            
            if total_count == 0:
                self.stdout.write(self.style.WARNING(f'⚠️  No questions found for "{chapter}" - SKIPPING'))
                chapters_with_no_questions.append(chapter)
                continue
            
            self.stdout.write(f'Found {total_count} questions')
            
            # Separate by paper
            has_paper_field = hasattr(model, 'paper')
            
            if has_paper_field:
                paper1_questions = [q for q in questions if 
                                    q.paper == '1' or 
                                    'paper1' in q.paper.lower() or 
                                    q.paper.lower() == 'paper 1']
                
                paper2_questions = [q for q in questions if 
                                    q.paper == '2' or 
                                    'paper2' in q.paper.lower() or 
                                    q.paper.lower() == 'paper 2']
                
                paper3_questions = [q for q in questions if 
                                    q.paper == '3' or 
                                    'paper3' in q.paper.lower() or 
                                    q.paper.lower() == 'paper 3']
                
                assigned_ids = [q.id for q in paper1_questions + paper2_questions + paper3_questions]
                other_questions = [q for q in questions if q.id not in assigned_ids]
                
                self.stdout.write(f'  - Paper 1: {len(paper1_questions)} questions')
                self.stdout.write(f'  - Paper 2: {len(paper2_questions)} questions')
                self.stdout.write(f'  - Paper 3: {len(paper3_questions)} questions')
                if other_questions:
                    self.stdout.write(f'  - Other: {len(other_questions)} questions')
            else:
                paper1_questions = list(questions)
                paper2_questions = []
                paper3_questions = []
                other_questions = []
            
            # Distribute
            free_questions = []
            registered_questions = []
            premium_questions = []
            
            # 1 FREE from Paper 1
            if paper1_questions:
                free_q = paper1_questions.pop(0)
                free_questions.append(free_q)
            
            # 2 REGISTERED (prefer 1 from Paper 2 + 1 from Paper 1)
            if paper2_questions:
                reg_q = paper2_questions.pop(0)
                registered_questions.append(reg_q)
            
            if paper1_questions:
                reg_q = paper1_questions.pop(0)
                registered_questions.append(reg_q)
            elif paper2_questions:
                reg_q = paper2_questions.pop(0)
                registered_questions.append(reg_q)
            
            # Rest are PREMIUM
            premium_questions = paper1_questions + paper2_questions + paper3_questions + other_questions
            
            self.stdout.write(f'  ✅ FREE: {len(free_questions)}')
            self.stdout.write(f'  ✅ REGISTERED: {len(registered_questions)}')
            self.stdout.write(f'  ✅ PREMIUM: {len(premium_questions)}')
            
            # Apply changes
            for q in free_questions:
                q.type = 'free'
                q.save()
            
            for q in registered_questions:
                q.type = 'registered'
                q.save()
            
            for q in premium_questions:
                q.type = 'premium'
                q.save()
            
                # Update totals
                total_chapters_processed += 1
                total_free += len(free_questions)
                total_registered += len(registered_questions)
                total_premium += len(premium_questions)
            
            # Subject summary
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.SUCCESS(f'📊 SUMMARY FOR {SUBJECT.upper()}'))
            self.stdout.write('=' * 70)
            self.stdout.write(f'Chapters processed: {total_chapters_processed}/{len(chapters)}')
            if chapters_with_no_questions:
                self.stdout.write(f'\nChapters with no questions (skipped): {len(chapters_with_no_questions)}')
                for ch in chapters_with_no_questions:
                    self.stdout.write(f'  - {ch}')
            
            self.stdout.write(f'\n📊 Questions Updated in {SUBJECT.upper()}:')
            self.stdout.write(f'  - FREE: {self.style.SUCCESS(total_free)}')
            self.stdout.write(f'  - REGISTERED: {self.style.WARNING(total_registered)}')
            self.stdout.write(f'  - PREMIUM: {self.style.ERROR(total_premium)}')
            self.stdout.write(f'  - TOTAL: {total_free + total_registered + total_premium}')
            
            # Update grand totals
            grand_total_chapters += total_chapters_processed
            grand_total_free += total_free
            grand_total_registered += total_registered
            grand_total_premium += total_premium
        
        # Final grand summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('🎉 GRAND TOTAL - ALL SUBJECTS'))
        self.stdout.write('=' * 70)
        self.stdout.write('=' * 70)
        self.stdout.write(f'\nSubjects processed: {len(subjects_to_process)}')
        self.stdout.write(f'Total chapters processed: {grand_total_chapters}')
        
        self.stdout.write(f'\n📊 Grand Total Questions Updated:')
        self.stdout.write(f'  - FREE: {self.style.SUCCESS(grand_total_free)}')
        self.stdout.write(f'  - REGISTERED: {self.style.WARNING(grand_total_registered)}')
        self.stdout.write(f'  - PREMIUM: {self.style.ERROR(grand_total_premium)}')
        self.stdout.write(f'  - TOTAL: {grand_total_free + grand_total_registered + grand_total_premium}')
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('✅ ALL SUBJECTS COMPLETED!'))
        self.stdout.write('=' * 70)
