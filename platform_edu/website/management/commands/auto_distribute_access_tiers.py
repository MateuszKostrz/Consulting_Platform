"""
Django management command to automatically distribute access tiers for a chapter.

Rules:
- 1 question from Paper 1 → 'free'
- 2 questions → 'registered' (1 from Paper 2 + 1 from Paper 1, or both from Paper 1 if no Paper 2)
- All remaining questions → 'premium'

Usage:
    python manage.py auto_distribute_access_tiers
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from website.models import (
    Math_AI_SL_Questionbank,
    Math_AI_HL_Questionbank,
    Math_AA_SL_Questionbank,
    Math_AA_HL_Questionbank,
    Physics_SL_Questionbank,
    Physics_HL_Questionbank,
    Biology_SL_Questionbank,
    Biology_HL_Questionbank,
    Comp_Sci_SL_Questionbank,
    Comp_Sci_HL_Questionbank,
)

# ======================== CONFIGURATION ========================
# Choose your subject (uncomment the one you want to use):
# SUBJECT = 'math_ai_sl'
# SUBJECT = 'math_ai_hl'
# SUBJECT = 'math_aa_hl'
# SUBJECT = 'math_aa_sl'
# SUBJECT = 'physics_hl'
SUBJECT = 'physics_sl'
# SUBJECT = 'biology_hl'
# SUBJECT = 'biology_sl'
# SUBJECT = 'comp_sci_sl'
# SUBJECT = 'comp_sci_hl'

# Choose your chapter (use the key from the CHAPTERS list in models.py)
# Math AI SL/HL chapters: 'number_skills', 'algebra', 'geometry_and_trigonometry', 
#   'statistics_and_probability', 'calculus'
# Math AA SL/HL chapters: 'number_and_algebra', 'functions', 'geometry_and_trigonometry', 
#   'statistics_and_probability', 'calculus'
# Physics SL/HL chapters: 'measurement_and_uncertainties', 'mechanics', 'thermal_physics', 
#   'waves', 'electricity_and_magnetism', 'circular_motion_and_gravitation', 
#   'atomic_nuclear_particle_physics', 'energy_production', 'wave_phenomena',
#   'fields', 'electromagnetic_induction', 'quantum_and_nuclear_physics',
#   'relativity', 'engineering_physics', 'imaging', 'astrophysics'
# Biology SL/HL chapters: 'cell_biology', 'molecular_biology', 'genetics', 
#   'ecology', 'evolution_and_biodiversity', 'human_physiology',
#   'nucleic_acids', 'metabolism_cell_respiration_and_photosynthesis',
#   'plant_biology', 'genetics_and_evolution', 'animal_physiology'
# Comp Sci SL/HL chapters: 'system_fundamentals', 'computer_organisation', 'networks',
#   'computational_thinking', 'variables_input', 'if_statements', 'loops',
#   'arrays', 'methods', 'constructors', 'oop'

CHAPTER = 'forces_and_momentum'
# ===============================================================


class Command(BaseCommand):
    help = 'Automatically distribute access tiers for questions in a chapter'
    
    # Map subject names to their respective models
    SUBJECT_MODELS = {
        'math_ai_sl': Math_AI_SL_Questionbank,
        'math_ai_hl': Math_AI_HL_Questionbank,
        'math_aa_sl': Math_AA_SL_Questionbank,
        'math_aa_hl': Math_AA_HL_Questionbank,
        'physics_sl': Physics_SL_Questionbank,
        'physics_hl': Physics_HL_Questionbank,
        'biology_sl': Biology_SL_Questionbank,
        'biology_hl': Biology_HL_Questionbank,
        'comp_sci_sl': Comp_Sci_SL_Questionbank,
        'comp_sci_hl': Comp_Sci_HL_Questionbank,
    }
    
    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('AUTO DISTRIBUTE ACCESS TIERS'))
        self.stdout.write('=' * 70)
        
        # Validate subject
        if SUBJECT not in self.SUBJECT_MODELS:
            self.stdout.write(self.style.ERROR(f'Invalid SUBJECT: {SUBJECT}'))
            self.stdout.write(f'Valid options: {", ".join(self.SUBJECT_MODELS.keys())}')
            return
        
        model = self.SUBJECT_MODELS[SUBJECT]
        
        self.stdout.write(f'\n📚 Subject: {self.style.WARNING(SUBJECT.upper())}')
        self.stdout.write(f'📖 Chapter: {self.style.WARNING(CHAPTER)}')
        self.stdout.write('\n' + '-' * 70)
        
        # Find all questions in this chapter (check which chapter fields exist)
        # Build query dynamically based on available fields
        query = Q(chapter=CHAPTER)
        
        # Check if model has chapter2 field
        if hasattr(model, 'chapter2'):
            field_names = [f.name for f in model._meta.get_fields()]
            if 'chapter2' in field_names:
                query |= Q(chapter2=CHAPTER)
            if 'chapter3' in field_names:
                query |= Q(chapter3=CHAPTER)
        
        questions = model.objects.filter(query).order_by('id')
        
        total_count = questions.count()
        
        if total_count == 0:
            self.stdout.write(self.style.ERROR(f'\n❌ No questions found for chapter "{CHAPTER}"'))
            return
        
        self.stdout.write(f'\n📊 Total questions found: {self.style.SUCCESS(total_count)}')
        
        # Separate questions by paper (if paper field exists)
        has_paper_field = hasattr(model, 'paper')
        
        if has_paper_field:
            # Debug: Check what paper values actually exist
            paper_values = list(questions.values_list('paper', flat=True).distinct())
            self.stdout.write(f'\n🔍 DEBUG: Unique paper values in database: {paper_values}')
            
            # Filter Paper 1 questions (handles both '1', 'paper1', 'paper1A', 'paper1B', etc.)
            paper1_questions = [q for q in questions if 
                                q.paper == '1' or 
                                'paper1' in q.paper.lower() or 
                                q.paper.lower() == 'paper 1']
            
            # Filter Paper 2 questions (handles both '2', 'paper2', 'paper 2', etc.)
            paper2_questions = [q for q in questions if 
                                q.paper == '2' or 
                                'paper2' in q.paper.lower() or 
                                q.paper.lower() == 'paper 2']
            
            # Filter Paper 3 questions
            paper3_questions = [q for q in questions if 
                                q.paper == '3' or 
                                'paper3' in q.paper.lower() or 
                                q.paper.lower() == 'paper 3']
            
            # Get all paper1, paper2, paper3 IDs to exclude from "other"
            assigned_ids = [q.id for q in paper1_questions + paper2_questions + paper3_questions]
            other_questions = list(questions.exclude(id__in=assigned_ids))
            
            self.stdout.write(f'  - Paper 1 questions: {len(paper1_questions)}')
            if paper1_questions:
                self.stdout.write(f'    IDs: {[q.id for q in paper1_questions[:5]]}{"..." if len(paper1_questions) > 5 else ""}')
            self.stdout.write(f'  - Paper 2 questions: {len(paper2_questions)}')
            if paper2_questions:
                self.stdout.write(f'    IDs: {[q.id for q in paper2_questions[:5]]}{"..." if len(paper2_questions) > 5 else ""}')
            self.stdout.write(f'  - Paper 3 questions: {len(paper3_questions)}')
            if paper3_questions:
                self.stdout.write(f'    IDs: {[q.id for q in paper3_questions[:5]]}{"..." if len(paper3_questions) > 5 else ""}')
            if other_questions:
                self.stdout.write(f'  - Other/No paper: {len(other_questions)}')
                self.stdout.write(f'    IDs: {[q.id for q in other_questions[:5]]}{"..." if len(other_questions) > 5 else ""}')
        else:
            # If no paper field, treat all as Paper 1
            paper1_questions = list(questions)
            paper2_questions = []
            paper3_questions = []
            other_questions = []
            self.stdout.write(self.style.WARNING('  ℹ️  Model has no "paper" field, treating all questions as Paper 1'))
        
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write(self.style.WARNING('DISTRIBUTION STRATEGY:'))
        self.stdout.write('  1️⃣  1 question from Paper 1 → FREE')
        self.stdout.write('  2️⃣  2 questions → REGISTERED (1 from Paper 2 + 1 from Paper 1, or both from Paper 1)')
        self.stdout.write('  3️⃣  All remaining questions → PREMIUM')
        self.stdout.write('-' * 70 + '\n')
        
        # Initialize counters
        free_questions = []
        registered_questions = []
        premium_questions = []
        
        # STEP 1: Select 1 FREE question from Paper 1
        if paper1_questions:
            free_q = paper1_questions.pop(0)  # Take first Paper 1 question
            free_questions.append(free_q)
            self.stdout.write(f'✅ FREE: Question #{free_q.id} (Paper 1)')
        else:
            self.stdout.write(self.style.ERROR('❌ No Paper 1 questions available for FREE tier'))
        
        # STEP 2: Select 2 REGISTERED questions
        # Try to get 1 from Paper 2 and 1 from Paper 1
        if paper2_questions:
            reg_q = paper2_questions.pop(0)
            registered_questions.append(reg_q)
            self.stdout.write(f'✅ REGISTERED: Question #{reg_q.id} (Paper 2)')
        
        if paper1_questions:
            reg_q = paper1_questions.pop(0)
            registered_questions.append(reg_q)
            self.stdout.write(f'✅ REGISTERED: Question #{reg_q.id} (Paper 1)')
        elif paper2_questions:
            # If no more Paper 1, use another Paper 2
            reg_q = paper2_questions.pop(0)
            registered_questions.append(reg_q)
            self.stdout.write(f'✅ REGISTERED: Question #{reg_q.id} (Paper 2)')
        
        if len(registered_questions) < 2:
            self.stdout.write(self.style.WARNING(f'⚠️  Only {len(registered_questions)} question(s) set as REGISTERED (needed 2)'))
        
        # STEP 3: All remaining questions become PREMIUM
        premium_questions = paper1_questions + paper2_questions + paper3_questions + other_questions
        
        self.stdout.write(f'\n📊 DISTRIBUTION SUMMARY:')
        self.stdout.write(f'  - FREE: {self.style.SUCCESS(len(free_questions))} question(s)')
        if free_questions:
            self.stdout.write(f'    IDs: {[q.id for q in free_questions]}')
        self.stdout.write(f'  - REGISTERED: {self.style.WARNING(len(registered_questions))} question(s)')
        if registered_questions:
            self.stdout.write(f'    IDs: {[q.id for q in registered_questions]}')
        self.stdout.write(f'  - PREMIUM: {self.style.ERROR(len(premium_questions))} question(s)')
        if premium_questions:
            self.stdout.write(f'    IDs: {[q.id for q in premium_questions]}')
        self.stdout.write(f'  - TOTAL: {len(free_questions) + len(registered_questions) + len(premium_questions)}')
        
        # Ask for confirmation
        self.stdout.write('\n' + '=' * 70)
        confirm = input('⚠️  Apply these changes? (yes/no): ')
        
        if confirm.lower() not in ['yes', 'y']:
            self.stdout.write(self.style.WARNING('\n❌ Operation cancelled.'))
            return
        
        # Apply changes
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('Applying changes...\n')
        
        free_count = 0
        for q in free_questions:
            self.stdout.write(f'  Setting Question #{q.id} to FREE...')
            q.type = 'free'
            q.save()
            free_count += 1
        
        reg_count = 0
        for q in registered_questions:
            self.stdout.write(f'  Setting Question #{q.id} to REGISTERED...')
            q.type = 'registered'
            q.save()
            reg_count += 1
        
        prem_count = 0
        for q in premium_questions:
            self.stdout.write(f'  Setting Question #{q.id} to PREMIUM...')
            q.type = 'premium'
            q.save()
            prem_count += 1
        
        self.stdout.write('\n' + self.style.SUCCESS(f'✅ Updated {free_count} question(s) to FREE'))
        self.stdout.write(self.style.SUCCESS(f'✅ Updated {reg_count} question(s) to REGISTERED'))
        self.stdout.write(self.style.SUCCESS(f'✅ Updated {prem_count} question(s) to PREMIUM'))
        
        # Verify the changes
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('Verifying changes...\n')
        
        verify_free = model.objects.filter(query, type='free').count()
        verify_registered = model.objects.filter(query, type='registered').count()
        verify_premium = model.objects.filter(query, type='premium').count()
        
        self.stdout.write(f'  FREE in database: {verify_free}')
        self.stdout.write(f'  REGISTERED in database: {verify_registered}')
        self.stdout.write(f'  PREMIUM in database: {verify_premium}')
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('✅ OPERATION COMPLETED SUCCESSFULLY!'))
        self.stdout.write('=' * 70)
