"""
Django Management Command: Fix Physics SL sync status

This command analyzes the actual sync status between SL and HL questions
and updates the sync_to_hl and hl_question_id fields to reflect reality.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from website.models import Physics_SL_Questionbank, Physics_HL_Questionbank
import hashlib

class Command(BaseCommand):
    help = 'Fix Physics SL sync status to reflect actual sync with HL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Show analysis of sync status without making changes',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix the sync status and links',
        )

    def handle(self, *args, **options):
        if options['analyze']:
            self.analyze_sync_status()
        elif options['fix']:
            self.fix_sync_status()
        else:
            self.stdout.write(self.style.WARNING('Usage:'))
            self.stdout.write('  python manage.py fix_physics_sync_status --analyze    # Show analysis')
            self.stdout.write('  python manage.py fix_physics_sync_status --fix       # Fix sync status')

    def get_question_hash(self, question_text):
        """Create a hash of the question text for matching"""
        cleaned_text = ' '.join(question_text.strip().lower().split())
        return hashlib.md5(cleaned_text.encode()).hexdigest()

    def find_matching_hl_question(self, sl_question):
        """Find matching HL question for an SL question"""
        # First try exact text match
        hl_question = Physics_HL_Questionbank.objects.filter(
            chapter=sl_question.chapter,
            question=sl_question.question
        ).first()
        
        if hl_question:
            return hl_question
        
        # Try hash matching for slight variations
        sl_hash = self.get_question_hash(sl_question.question)
        hl_questions = Physics_HL_Questionbank.objects.filter(chapter=sl_question.chapter)
        
        for hl_q in hl_questions:
            if self.get_question_hash(hl_q.question) == sl_hash:
                return hl_q
        
        return None

    def analyze_sync_status(self):
        """Analyze the current sync status"""
        self.stdout.write(self.style.SUCCESS('🔬 Physics SL/HL Sync Status Analysis'))
        self.stdout.write('=' * 60)
        
        # Get all SL questions
        sl_questions = Physics_SL_Questionbank.objects.all().order_by('chapter', 'id')
        
        stats = {
            'total_sl': 0,
            'marked_sync_true': 0,
            'marked_sync_false': 0,
            'actually_synced': 0,
            'marked_true_but_not_synced': 0,
            'marked_false_but_synced': 0,
            'correct_links': 0,
            'broken_links': 0,
            'missing_links': 0
        }
        
        issues = []
        
        for sl_q in sl_questions:
            stats['total_sl'] += 1
            
            # Check current sync setting
            if sl_q.sync_to_hl:
                stats['marked_sync_true'] += 1
            else:
                stats['marked_sync_false'] += 1
            
            # Check if HL question actually exists
            matching_hl = self.find_matching_hl_question(sl_q)
            
            if matching_hl:
                stats['actually_synced'] += 1
                
                # Check if link is correct
                if sl_q.hl_question_id == matching_hl.id:
                    stats['correct_links'] += 1
                elif sl_q.hl_question_id is None:
                    stats['missing_links'] += 1
                    issues.append(f"SL {sl_q.id}: Missing link to HL {matching_hl.id}")
                else:
                    stats['broken_links'] += 1
                    issues.append(f"SL {sl_q.id}: Wrong link {sl_q.hl_question_id}, should be {matching_hl.id}")
                
                # Check sync setting accuracy
                if not sl_q.sync_to_hl:
                    stats['marked_false_but_synced'] += 1
                    issues.append(f"SL {sl_q.id}: Marked sync=False but HL question exists")
            else:
                # No matching HL question
                if sl_q.sync_to_hl:
                    stats['marked_true_but_not_synced'] += 1
                    issues.append(f"SL {sl_q.id}: Marked sync=True but no HL question exists")
                
                if sl_q.hl_question_id is not None:
                    stats['broken_links'] += 1
                    issues.append(f"SL {sl_q.id}: Has link {sl_q.hl_question_id} but HL question doesn't exist")
        
        # Print statistics
        self.stdout.write(f"\n📊 STATISTICS:")
        self.stdout.write(f"{'Total SL questions:':<35} {stats['total_sl']}")
        self.stdout.write(f"{'Marked sync_to_hl=True:':<35} {stats['marked_sync_true']}")
        self.stdout.write(f"{'Marked sync_to_hl=False:':<35} {stats['marked_sync_false']}")
        self.stdout.write(f"{'Actually have HL match:':<35} {stats['actually_synced']}")
        self.stdout.write("")
        self.stdout.write(f"{'✅ Correct links:':<35} {stats['correct_links']}")
        self.stdout.write(f"{'🔗 Missing links:':<35} {stats['missing_links']}")
        self.stdout.write(f"{'❌ Broken links:':<35} {stats['broken_links']}")
        self.stdout.write("")
        self.stdout.write(f"{'⚠️  Marked True but no HL:':<35} {stats['marked_true_but_not_synced']}")
        self.stdout.write(f"{'⚠️  Marked False but has HL:':<35} {stats['marked_false_but_synced']}")
        
        # Show some sample issues
        if issues:
            self.stdout.write(f"\n🔍 SAMPLE ISSUES (showing first 10):")
            for issue in issues[:10]:
                self.stdout.write(f"  • {issue}")
            
            if len(issues) > 10:
                self.stdout.write(f"  ... and {len(issues) - 10} more issues")

    def fix_sync_status(self):
        """Fix the sync status and links"""
        self.stdout.write(self.style.SUCCESS('🔧 Fixing Physics SL/HL Sync Status'))
        self.stdout.write('=' * 50)
        
        fixed_count = 0
        
        with transaction.atomic():
            sl_questions = Physics_SL_Questionbank.objects.all()
            
            for sl_q in sl_questions:
                original_sync = sl_q.sync_to_hl
                original_link = sl_q.hl_question_id
                
                # Find matching HL question
                matching_hl = self.find_matching_hl_question(sl_q)
                
                if matching_hl:
                    # HL question exists - should be synced
                    sl_q.sync_to_hl = True
                    sl_q.hl_question_id = matching_hl.id
                else:
                    # No HL question - should not be synced
                    sl_q.sync_to_hl = False
                    sl_q.hl_question_id = None
                
                # Save if changed
                if (sl_q.sync_to_hl != original_sync or 
                    sl_q.hl_question_id != original_link):
                    sl_q.save()
                    fixed_count += 1
                    
                    action = "SYNCED" if sl_q.sync_to_hl else "UNSYNCED"
                    self.stdout.write(f"Fixed SL {sl_q.id}: {action} (link: {sl_q.hl_question_id})")
        
        self.stdout.write(f"\n✅ Fixed {fixed_count} questions")
        self.stdout.write("🔍 Run --analyze again to see the updated status")
