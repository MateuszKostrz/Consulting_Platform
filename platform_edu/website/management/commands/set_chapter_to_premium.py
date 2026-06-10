from django.core.management.base import BaseCommand
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
from django.db.models import Q


# ============================================================================
# CONFIGURATION - EDIT THIS SECTION
# ============================================================================

# Choose your subject (uncomment the one you want to use):
# SUBJECT = 'math_aa_hl'
# SUBJECT = 'math_aa_sl'
SUBJECT = 'math_ai_hl'
# SUBJECT = 'math_aa_sl'
# SUBJECT = 'physics_hl'
# SUBJECT = 'physics_sl'
# SUBJECT = 'biology_hl'
# SUBJECT = 'biology_sl'
# SUBJECT = 'comp_sci_hl'
# SUBJECT = 'comp_sci_sl'

# Choose your chapter (use the key from the CHAPTERS list in models.py)
# For Math AI SL/HL chapters, use one of:
#   'number_skills', 'seq_series', 'systems_lin_eq', 'lin_eq_graphs',
#   'hypothesis_testing', 'trigonometry', 'applications_of_functions',
#   'voronoi_diagrams', 'probability', 'properties_of_functions',
#   'integration', 'distributions', 'geometry_shapes', 'descriptive_stats',
#   'differentiation', 'bivariate_statistics'

CHAPTER = 'integration'

# Access tier to set (options: 'free', 'registered', 'premium')
ACCESS_TIER = 'premium'

# ============================================================================
# END CONFIGURATION
# ============================================================================


class Command(BaseCommand):
    help = 'Set all questions from a specific chapter to a specific access tier (default: premium)'

    # Map subject names to models
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
        self.stdout.write('\n' + '='*70)
        self.stdout.write('Chapter Access Tier Management')
        self.stdout.write('='*70 + '\n')
        
        # Validate subject
        if SUBJECT not in self.SUBJECT_MODELS:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: Unknown subject "{SUBJECT}"'))
            self.stdout.write('Available subjects:')
            for subject in sorted(self.SUBJECT_MODELS.keys()):
                self.stdout.write(f'  - {subject}')
            return
        
        # Validate access tier
        valid_tiers = ['free', 'registered', 'premium']
        if ACCESS_TIER not in valid_tiers:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: Invalid access tier "{ACCESS_TIER}"'))
            self.stdout.write(f'Valid options: {", ".join(valid_tiers)}')
            return
        
        model = self.SUBJECT_MODELS[SUBJECT]
        total_questions = model.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Subject: {SUBJECT}'))
        self.stdout.write(f'  Total questions in database: {total_questions}')
        self.stdout.write(self.style.SUCCESS(f'✓ Chapter: {CHAPTER}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Target access tier: {ACCESS_TIER.upper()}\n'))
        
        # Get chapter display name if available
        chapter_name = self.get_chapter_display_name(model, CHAPTER)
        if chapter_name:
            self.stdout.write(f'  Chapter display name: "{chapter_name}"\n')
        
        # Find all questions in this chapter
        # A question belongs to a chapter if it's in chapter, chapter2, or chapter3
        questions = model.objects.filter(
            Q(chapter=CHAPTER) | Q(chapter2=CHAPTER) | Q(chapter3=CHAPTER)
        )
        
        question_count = questions.count()
        
        if question_count == 0:
            self.stdout.write(self.style.WARNING(f'\n⚠ No questions found in chapter "{CHAPTER}"'))
            self.stdout.write('  Please check that the chapter key is correct.\n')
            
            # Show available chapters
            self.show_available_chapters(model)
            return
        
        # Get current distribution
        free_count = questions.filter(type='free').count()
        registered_count = questions.filter(type='registered').count()
        premium_count = questions.filter(type='premium').count()
        
        # Display current status
        self.stdout.write('='*70)
        self.stdout.write('CURRENT STATUS')
        self.stdout.write('='*70)
        self.stdout.write(f'\n  Total questions in "{CHAPTER}": {question_count}')
        self.stdout.write(f'\n  Current distribution:')
        self.stdout.write(f'    - FREE:       {free_count} questions')
        self.stdout.write(f'    - REGISTERED: {registered_count} questions')
        self.stdout.write(f'    - PREMIUM:    {premium_count} questions\n')
        
        # Show some example question IDs
        example_ids = list(questions.values_list('id', flat=True)[:10])
        if len(example_ids) <= 10:
            self.stdout.write(f'  Question IDs: {example_ids}\n')
        else:
            self.stdout.write(f'  First 10 IDs: {example_ids} (and {question_count - 10} more)\n')
        
        # Confirm action
        self.stdout.write('='*70)
        self.stdout.write(self.style.WARNING('CONFIRMATION'))
        self.stdout.write('='*70)
        self.stdout.write(f'\nYou are about to set {question_count} questions to {ACCESS_TIER.upper()}.')
        self.stdout.write(f'Subject: {SUBJECT}')
        self.stdout.write(f'Chapter: {CHAPTER}\n')
        
        confirm = input('Do you want to proceed? (yes/no): ')
        
        if confirm.lower() not in ['yes', 'y']:
            self.stdout.write(self.style.WARNING('\n✗ Operation cancelled by user.\n'))
            return
        
        # Apply changes
        self.stdout.write('\nApplying changes...\n')
        
        updated = questions.update(type=ACCESS_TIER)
        
        self.stdout.write('='*70)
        self.stdout.write(self.style.SUCCESS(f'✓ Successfully updated {updated} questions to {ACCESS_TIER.upper()}!'))
        self.stdout.write('='*70)
        
        # Show final distribution
        free_count = questions.filter(type='free').count()
        registered_count = questions.filter(type='registered').count()
        premium_count = questions.filter(type='premium').count()
        
        self.stdout.write('\nFinal distribution:')
        self.stdout.write(f'  - FREE:       {free_count} questions')
        self.stdout.write(f'  - REGISTERED: {registered_count} questions')
        self.stdout.write(f'  - PREMIUM:    {premium_count} questions\n')
    
    def get_chapter_display_name(self, model, chapter_key):
        """Get the human-readable chapter name from the model"""
        if hasattr(model, 'CHAPTERS'):
            chapter_dict = dict(model.CHAPTERS)
            return chapter_dict.get(chapter_key, None)
        return None
    
    def show_available_chapters(self, model):
        """Display available chapters for this subject"""
        if hasattr(model, 'CHAPTERS'):
            self.stdout.write('\nAvailable chapters for this subject:')
            for key, name in model.CHAPTERS:
                if key:  # Skip empty option
                    # Count questions in this chapter
                    count = model.objects.filter(
                        Q(chapter=key) | Q(chapter2=key) | Q(chapter3=key)
                    ).count()
                    self.stdout.write(f'  - {key:30} ({name}, {count} questions)')
            self.stdout.write('')
