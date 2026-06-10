import re
from django.core.management.base import BaseCommand
from website.models import Math_AI_HL_Questionbank


class Command(BaseCommand):
    help = 'Update AI HL questions difficulty, papers, and subscription types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--chapter',
            type=str,
            default='number_skills',
            help='Chapter to update (default: number_skills)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes'
        )

    def handle(self, *args, **options):
        chapter = options['chapter']
        dry_run = options['dry_run']
        
        self.stdout.write(f'Processing AI HL questions for chapter: {chapter}')
        
        # Get all questions for the specified chapter
        questions = Math_AI_HL_Questionbank.objects.filter(chapter=chapter).order_by('id')
        
        if not questions:
            self.stdout.write(self.style.WARNING(f'No questions found for chapter: {chapter}'))
            return
        
        self.stdout.write(f'Found {questions.count()} questions')
        
        # Analyze and update questions
        updated_questions = []
        
        for question in questions:
            updates = self.analyze_question(question)
            if updates:
                updated_questions.append((question, updates))
        
        # Apply subscription type rules
        self.apply_subscription_rules(updated_questions)
        
        # Display results
        self.display_results(updated_questions, dry_run)
        
        # Apply changes if not dry run
        if not dry_run:
            self.apply_changes(updated_questions)
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {len(updated_questions)} questions'))
        else:
            self.stdout.write(self.style.WARNING('Dry run - no changes applied'))

    def analyze_question(self, question):
        """Analyze a question and determine its difficulty and paper type"""
        updates = {}
        
        # Determine paper type based on marks
        marks = self.extract_marks(question.marks)
        if marks > 11:
            updates['paper'] = 'paper2'
        else:
            updates['paper'] = 'paper1'
        
        # Determine difficulty based on question complexity
        difficulty = self.assess_difficulty(question.question, marks)
        updates['difficulty'] = difficulty
        
        return updates

    def extract_marks(self, marks_field):
        """Extract numeric marks from the marks field"""
        if not marks_field or marks_field == 'null':
            return 0
        
        try:
            # Try to convert directly to int
            return int(marks_field)
        except ValueError:
            # Extract number from string using regex
            match = re.search(r'\d+', str(marks_field))
            if match:
                return int(match.group())
            return 0

    def assess_difficulty(self, question_text, marks):
        """Assess question difficulty based on content and marks"""
        question_lower = question_text.lower()
        
        # Indicators of difficulty
        hard_indicators = [
            'prove', 'derive', 'show that', 'verify',
            'complex', 'advanced', 'logarithm', 'exponential function',
            'matrix', 'determinant', 'system of equations',
            'integral', 'derivative', 'differential',
            'trigonometric identity', 'compound angle'
        ]
        
        medium_indicators = [
            'solve', 'find', 'calculate', 'determine',
            'graph', 'plot', 'equation', 'function',
            'probability', 'statistics', 'sequence',
            'geometric', 'arithmetic', 'series'
        ]
        
        easy_indicators = [
            'simplify', 'evaluate', 'basic', 'simple',
            'addition', 'subtraction', 'multiplication', 'division',
            'substitute', 'round', 'approximate'
        ]
        
        # Count indicators
        hard_count = sum(1 for indicator in hard_indicators if indicator in question_lower)
        medium_count = sum(1 for indicator in medium_indicators if indicator in question_lower)
        easy_count = sum(1 for indicator in easy_indicators if indicator in question_lower)
        
        # Determine difficulty based on marks and content
        if marks >= 10 or hard_count >= 2:
            return 'Hard'
        elif marks >= 6 or hard_count >= 1 or medium_count >= 3:
            return 'Medium'
        elif easy_count >= 2 or marks <= 3:
            return 'Easy'
        else:
            # Default based on marks
            if marks >= 7:
                return 'Medium'
            else:
                return 'Easy'

    def apply_subscription_rules(self, updated_questions):
        """Apply subscription type rules: 2 easiest as free, 50% premium, rest registered"""
        total_questions = len(updated_questions)
        
        # Sort by difficulty (Easy first, then by marks)
        def sort_key(item):
            question, updates = item
            difficulty_order = {'Easy': 1, 'Medium': 2, 'Hard': 3}
            marks = self.extract_marks(question.marks)
            return (difficulty_order.get(updates['difficulty'], 2), marks)
        
        sorted_questions = sorted(updated_questions, key=sort_key)
        
        # Calculate distribution
        num_premium = total_questions // 2  # 50% premium
        num_free = min(2, total_questions)  # Max 2 free
        num_registered = total_questions - num_premium - num_free
        
        self.stdout.write(f'Distribution: {num_free} free, {num_registered} registered, {num_premium} premium')
        
        # Assign subscription types
        for i, (question, updates) in enumerate(sorted_questions):
            if i < num_free:
                updates['type'] = 'free'
            elif i < num_free + num_registered:
                updates['type'] = 'registered'
            else:
                updates['type'] = 'premium'

    def display_results(self, updated_questions, dry_run):
        """Display the results of the analysis"""
        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN RESULTS ==='))
        else:
            self.stdout.write(self.style.SUCCESS('\n=== CHANGES TO BE APPLIED ==='))
        
        # Group by changes
        difficulty_changes = {}
        paper_changes = {}
        type_changes = {}
        
        for question, updates in updated_questions:
            # Track difficulty changes
            old_difficulty = question.difficulty
            new_difficulty = updates.get('difficulty', old_difficulty)
            if old_difficulty != new_difficulty:
                if new_difficulty not in difficulty_changes:
                    difficulty_changes[new_difficulty] = []
                difficulty_changes[new_difficulty].append(f"Q{question.id}: {old_difficulty} → {new_difficulty}")
            
            # Track paper changes
            old_paper = question.paper
            new_paper = updates.get('paper', old_paper)
            if old_paper != new_paper:
                if new_paper not in paper_changes:
                    paper_changes[new_paper] = []
                paper_changes[new_paper].append(f"Q{question.id}: {old_paper} → {new_paper} (marks: {question.marks})")
            
            # Track type changes
            old_type = question.type
            new_type = updates.get('type', old_type)
            if old_type != new_type:
                if new_type not in type_changes:
                    type_changes[new_type] = []
                type_changes[new_type].append(f"Q{question.id}: {old_type} → {new_type}")
        
        # Display changes
        if difficulty_changes:
            self.stdout.write('\nDIFFICULTY CHANGES:')
            for difficulty, changes in difficulty_changes.items():
                self.stdout.write(f'  {difficulty}:')
                for change in changes:
                    self.stdout.write(f'    {change}')
        
        if paper_changes:
            self.stdout.write('\nPAPER CHANGES:')
            for paper, changes in paper_changes.items():
                self.stdout.write(f'  {paper}:')
                for change in changes:
                    self.stdout.write(f'    {change}')
        
        if type_changes:
            self.stdout.write('\nSUBSCRIPTION TYPE CHANGES:')
            for sub_type, changes in type_changes.items():
                self.stdout.write(f'  {sub_type}:')
                for change in changes:
                    self.stdout.write(f'    {change}')
        
        # Summary
        self.stdout.write('\nSUMMARY:')
        final_distribution = {'Easy': 0, 'Medium': 0, 'Hard': 0}
        paper_distribution = {'paper1': 0, 'paper2': 0}
        type_distribution = {'free': 0, 'registered': 0, 'premium': 0}
        
        for question, updates in updated_questions:
            final_distribution[updates.get('difficulty', question.difficulty)] += 1
            paper_distribution[updates.get('paper', question.paper)] += 1
            type_distribution[updates.get('type', question.type)] += 1
        
        self.stdout.write(f'  Difficulty: {dict(final_distribution)}')
        self.stdout.write(f'  Papers: {dict(paper_distribution)}')
        self.stdout.write(f'  Subscription: {dict(type_distribution)}')

    def apply_changes(self, updated_questions):
        """Apply the changes to the database"""
        for question, updates in updated_questions:
            for field, value in updates.items():
                setattr(question, field, value)
            question.save() 