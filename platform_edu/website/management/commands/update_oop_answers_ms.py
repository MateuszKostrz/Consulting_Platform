from django.core.management.base import BaseCommand
from website.models import Comp_Sci_SL_Questionbank, Math_AI_SL_Questionbank
import re


class Command(BaseCommand):
    help = 'Add answers-ms class to OOP questions in Computer Science SL questionbank'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Preview changes without updating database',
        )
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Execute the updates (required to make changes)',
        )
    
    def handle(self, *args, **options):
        if options['preview']:
            self.preview_changes()
        elif options['execute']:
            self.update_oop_answers()
        else:
            self.stdout.write(
                self.style.WARNING('Usage:')
            )
            self.stdout.write(
                '  python manage.py update_oop_answers_ms --preview    # Preview changes'
            )
            self.stdout.write(
                '  python manage.py update_oop_answers_ms --execute   # Apply changes'
            )
    
    def update_oop_answers(self):
        """
        Update OOP questions to add answers-ms class to paragraph tags containing (a), (b), etc.
        """
        self.stdout.write("🔍 Searching for OOP questions in Computer Science SL questionbank...")
        
        # Get all OOP questions
        oop_questions = Math_AI_SL_Questionbank.objects.filter(chapter='number_skills')
        
        if not oop_questions.exists():
            self.stdout.write(self.style.ERROR("❌ No OOP questions found in the database."))
            return
        
        self.stdout.write(f"📊 Found {oop_questions.count()} OOP questions to process.")
        
        updated_count = 0
        total_questions = oop_questions.count()
        
        for i, question in enumerate(oop_questions, 1):
            self.stdout.write(f"\n📝 Processing question {i}/{total_questions} (ID: {question.id})")
            
            original_answer = question.answer
            updated_answer = self.add_answers_ms_class(original_answer)
            
            if updated_answer != original_answer:
                question.answer = updated_answer
                question.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Updated question {question.id}"))
            else:
                self.stdout.write(f"⏭️  No changes needed for question {question.id}")
        
        self.stdout.write(f"\n🎉 Processing complete!")
        self.stdout.write(f"📊 Total questions processed: {total_questions}")
        self.stdout.write(self.style.SUCCESS(f"✅ Questions updated: {updated_count}"))
        self.stdout.write(f"⏭️  Questions unchanged: {total_questions - updated_count}")


    def add_answers_ms_class(self, html_content):
        """
        Add 'answers-ms' class to paragraph tags that contain strong tags with parentheses.
        
        Args:
            html_content (str): The HTML content to process
            
        Returns:
            str: Updated HTML content with answers-ms class added
        """
        if not html_content:
            return html_content
        
        # Pattern to match various formats:
        # <p><strong>(a)</strong>
        # <p><strong>a)</strong>
        # <p><strong>a) (i)</strong>
        # etc.
        
        pattern = r'<p><strong>(\([a-z]\)|[a-z]\)\s*(?: \([a-z]\))?)</strong>'
        
        def replace_func(match):
            # Get the full match to preserve the original format
            full_match = match.group(0)
            # Extract just the letter for the class
            letter = match.group(1)
            # Return the updated tag with answers-ms class, preserving original format
            return f'<p class="answers-ms">{full_match}'
        
        # Apply the replacement
        updated_content = re.sub(pattern, replace_func, html_content)
        
        return updated_content

    def preview_changes(self):
        """
        Preview what changes would be made without actually updating the database.
        """
        self.stdout.write("🔍 Previewing changes for OOP questions...")
        
        oop_questions = Math_AI_SL_Questionbank.objects.filter(chapter='number_skills')
        
        if not oop_questions.exists():
            self.stdout.write(self.style.ERROR("❌ No OOP questions found in the database."))
            return
        
        self.stdout.write(f"📊 Found {oop_questions.count()} OOP questions to preview.")
        
        changes_found = 0
        
        for i, question in enumerate(oop_questions, 1):
            original_answer = question.answer
            updated_answer = self.add_answers_ms_class(original_answer)
            
            if updated_answer != original_answer:
                changes_found += 1
                self.stdout.write(f"\n📝 Question {i} (ID: {question.id}) would be updated:")
                self.stdout.write("BEFORE:")
                self.stdout.write(self.extract_relevant_lines(original_answer))
                self.stdout.write("AFTER:")
                self.stdout.write(self.extract_relevant_lines(updated_answer))
                self.stdout.write("-" * 50)
        
        self.stdout.write(f"\n📊 Preview complete!")
        self.stdout.write(self.style.SUCCESS(f"✅ Questions that would be updated: {changes_found}"))
        self.stdout.write(f"⏭️  Questions that would remain unchanged: {oop_questions.count() - changes_found}")

    def extract_relevant_lines(self, html_content, max_lines=5):
        """
        Extract relevant lines from HTML content for preview.
        """
        lines = html_content.split('\n')
        relevant_lines = []
        
        for line in lines:
            if ('<p><strong>' in line and ')</strong>' in line) or '<p class="answers-ms"><strong>' in line:
                relevant_lines.append(line.strip())
                if len(relevant_lines) >= max_lines:
                    break
        
        return '\n'.join(relevant_lines)
