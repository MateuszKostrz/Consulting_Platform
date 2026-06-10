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


# ============================================================================
# CONFIGURATION - EDIT THIS SECTION
# ============================================================================

# Choose your subject (uncomment the one you want to use):
SUBJECT = 'math_aa_hl'
# SUBJECT = 'math_aa_sl'
# SUBJECT = 'math_ai_hl'
# SUBJECT = 'math_ai_sl'
# SUBJECT = 'physics_hl'
# SUBJECT = 'physics_sl'
# SUBJECT = 'biology_hl'
# SUBJECT = 'biology_sl'
# SUBJECT = 'comp_sci_hl'
# SUBJECT = 'comp_sci_sl'

# FREE question IDs (comma-separated or ranges)
# Examples: "1,2,3" or "1-10" or "1,5,10-15"
FREE_IDS = "1-5"

# REGISTERED question IDs (comma-separated or ranges)
# Examples: "11,12,13" or "11-20" or "11,15,20-25"
REGISTERED_IDS = "6-20"

# All other questions will automatically be set to PREMIUM

# ============================================================================
# END CONFIGURATION
# ============================================================================


class Command(BaseCommand):
    help = 'Set access tiers (free/registered/premium) for questionbank questions by subject'

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
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Question Access Tier Management')
        self.stdout.write('='*60 + '\n')
        
        # Validate subject
        if SUBJECT not in self.SUBJECT_MODELS:
            self.stdout.write(self.style.ERROR(f'\nError: Unknown subject "{SUBJECT}"'))
            self.stdout.write('Available subjects:')
            for subject in sorted(self.SUBJECT_MODELS.keys()):
                self.stdout.write(f'  - {subject}')
            return
        
        model = self.SUBJECT_MODELS[SUBJECT]
        total_questions = model.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Selected: {SUBJECT}'))
        self.stdout.write(f'  Total questions in database: {total_questions}\n')
        
        # Parse IDs
        free_ids = self.parse_ids(FREE_IDS)
        registered_ids = self.parse_ids(REGISTERED_IDS)
        
        # Check for overlaps
        overlap = free_ids & registered_ids
        if overlap:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: IDs {sorted(overlap)} appear in both FREE and REGISTERED!'))
            self.stdout.write('  Please fix the configuration and try again.')
            return
        
        # Calculate premium IDs (all others)
        all_existing_ids = set(model.objects.values_list('id', flat=True))
        specified_ids = free_ids | registered_ids
        premium_ids = all_existing_ids - specified_ids
        
        # Check if any specified IDs don't exist
        missing_ids = (free_ids | registered_ids) - all_existing_ids
        if missing_ids:
            self.stdout.write(self.style.WARNING(f'\n⚠ Warning: IDs {sorted(missing_ids)} do not exist in database'))
            self.stdout.write('  These will be ignored.')
            free_ids -= missing_ids
            registered_ids -= missing_ids
        
        # Display summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('SUMMARY')
        self.stdout.write('='*60)
        self.stdout.write(f'\n  FREE questions:       {len(free_ids)} question(s)')
        if free_ids:
            self.stdout.write(f'    IDs: {self.format_id_ranges(sorted(free_ids))}')
        
        self.stdout.write(f'\n  REGISTERED questions: {len(registered_ids)} question(s)')
        if registered_ids:
            self.stdout.write(f'    IDs: {self.format_id_ranges(sorted(registered_ids))}')
        
        self.stdout.write(f'\n  PREMIUM questions:    {len(premium_ids)} question(s)')
        if premium_ids and len(premium_ids) <= 20:
            self.stdout.write(f'    IDs: {self.format_id_ranges(sorted(premium_ids))}')
        elif premium_ids:
            preview_ids = sorted(list(premium_ids)[:10])
            self.stdout.write(f'    IDs: {self.format_id_ranges(preview_ids)} ... (and {len(premium_ids)-10} more)')
        
        self.stdout.write('\n' + '-'*60)
        
        # Apply changes
        self.stdout.write('\nApplying changes...\n')
        
        # Update free questions
        if free_ids:
            updated = model.objects.filter(id__in=free_ids).update(type='free')
            self.stdout.write(self.style.SUCCESS(f'✓ Set {updated} questions to FREE'))
        
        # Update registered questions
        if registered_ids:
            updated = model.objects.filter(id__in=registered_ids).update(type='registered')
            self.stdout.write(self.style.SUCCESS(f'✓ Set {updated} questions to REGISTERED'))
        
        # Update premium questions
        if premium_ids:
            updated = model.objects.filter(id__in=premium_ids).update(type='premium')
            self.stdout.write(self.style.SUCCESS(f'✓ Set {updated} questions to PREMIUM'))
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✓ All changes applied successfully!'))
        self.stdout.write('='*60 + '\n')
    
    def parse_ids(self, input_str):
        """
        Parse ID input string and return a set of IDs.
        Supports: "1,2,3" or "1-10" or "1,5,10-15"
        """
        if not input_str:
            return set()
        
        ids = set()
        parts = input_str.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Handle range (e.g., "1-10")
                try:
                    start, end = part.split('-')
                    start = int(start.strip())
                    end = int(end.strip())
                    ids.update(range(start, end + 1))
                except ValueError:
                    self.stdout.write(self.style.WARNING(f'Warning: Invalid range "{part}", skipping...'))
            else:
                # Handle single ID
                try:
                    ids.add(int(part))
                except ValueError:
                    if part:  # Ignore empty strings
                        self.stdout.write(self.style.WARNING(f'Warning: Invalid ID "{part}", skipping...'))
        
        return ids
    
    def format_id_ranges(self, ids):
        """
        Format a list of IDs into a compact string with ranges.
        Example: [1,2,3,5,7,8,9] -> "1-3, 5, 7-9"
        """
        if not ids:
            return ""
        
        ranges = []
        start = ids[0]
        end = ids[0]
        
        for i in range(1, len(ids)):
            if ids[i] == end + 1:
                end = ids[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = ids[i]
                end = ids[i]
        
        # Add the last range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
        
        return ", ".join(ranges)
