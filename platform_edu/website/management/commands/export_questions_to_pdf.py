from django.core.management.base import BaseCommand
from website.models import Comp_Sci_SL_Questionbank
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime


class Command(BaseCommand):
    help = 'Export Computer Science SL System Fundamentals questions to PDF'

    def add_arguments(self, parser):
        parser.add_argument(
            '--chapter',
            type=str,
            default='system_fundamentals',
            help='Chapter to export (default: system_fundamentals)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='system_fundamentals_questions.pdf',
            help='Output PDF filename'
        )

    def extract_content_with_code(self, html_content):
        """Extract content preserving code blocks"""
        if not html_content:
            return []
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        elements = []
        
        # Process each element in the soup
        for element in soup.descendants:
            if element.name == 'pre' or element.name == 'code':
                # Extract code text
                code_text = element.get_text()
                elements.append(('code', code_text))
            elif element.name == 'p' or element.name == 'div':
                # Check if this paragraph contains code
                code_blocks = element.find_all(['pre', 'code'])
                if code_blocks:
                    # Process mixed content
                    for child in element.children:
                        if child.name in ['pre', 'code']:
                            code_text = child.get_text()
                            elements.append(('code', code_text))
                        elif hasattr(child, 'get_text'):
                            text = child.get_text().strip()
                            if text:
                                elements.append(('text', text))
                        elif isinstance(child, str):
                            text = child.strip()
                            if text:
                                elements.append(('text', text))
                else:
                    # Regular text
                    text = element.get_text().strip()
                    if text and element.parent.name != 'code' and element.parent.name != 'pre':
                        elements.append(('text', text))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_elements = []
        for elem_type, content in elements:
            # Create a unique key
            key = (elem_type, content)
            if key not in seen and content:
                seen.add(key)
                unique_elements.append((elem_type, content))
        
        return unique_elements
    
    def clean_html(self, html_content):
        """Remove HTML tags and clean up the content (for backward compatibility)"""
        if not html_content:
            return ""
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get text content
        text = soup.get_text()
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text

    def handle(self, *args, **options):
        chapter = options['chapter']
        output_filename = options['output']
        
        # Get all questions from the specified chapter
        questions = Comp_Sci_SL_Questionbank.objects.filter(
            chapter=chapter
        ).order_by('id')
        
        if not questions.exists():
            self.stdout.write(self.style.ERROR(f'No questions found for chapter: {chapter}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {questions.count()} questions for {chapter}'))
        
        # Create PDF
        output_path = os.path.join('/Users/mateuszkostrz/Desktop/PLATFORM NEW PUBLISH/Edunade_Platform/platform_edu', output_filename)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#2c3e50',
            spaceAfter=30,
            alignment=TA_LEFT
        )
        
        # Question heading style
        question_heading_style = ParagraphStyle(
            'QuestionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor='#34495e',
            spaceAfter=12,
            spaceBefore=20,
            alignment=TA_LEFT
        )
        
        # Content style
        content_style = ParagraphStyle(
            'Content',
            parent=styles['BodyText'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )
        
        # Code style
        code_style = ParagraphStyle(
            'Code',
            parent=styles['Code'],
            fontSize=9,
            leading=12,
            fontName='Courier',
            textColor=HexColor('#2c3e50'),
            backColor=HexColor('#f4f4f4'),
            leftIndent=20,
            rightIndent=20,
            spaceBefore=6,
            spaceAfter=6,
            borderPadding=8,
            borderWidth=1,
            borderColor=HexColor('#ddd')
        )
        
        # Add title
        chapter_display = chapter.replace('_', ' ').title()
        title = Paragraph(f"Computer Science SL - {chapter_display}", title_style)
        elements.append(title)
        
        date_text = Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", content_style)
        elements.append(date_text)
        elements.append(Spacer(1, 0.3*inch))
        
        # Add each question
        for idx, question in enumerate(questions, 1):
            # Question heading
            question_title = Paragraph(f"<b>Question {idx}</b>", question_heading_style)
            elements.append(question_title)
            
            # Question content - raw from database
            if question.question:
                elements.append(Paragraph("<b>Question:</b>", content_style))
                # Show raw HTML/code from database
                question_pre = Preformatted(question.question, code_style)
                elements.append(question_pre)
                elements.append(Spacer(1, 0.1*inch))
            
            # Paper and difficulty info
            paper_display = question.paper.replace('_', ' ').title() if question.paper else 'N/A'
            difficulty_display = question.difficulty.title() if question.difficulty else 'N/A'
            marks_display = question.marks if question.marks else 'N/A'
            
            info_text = f"<i>Paper: {paper_display} | Difficulty: {difficulty_display} | Marks: {marks_display}</i>"
            info_para = Paragraph(info_text, content_style)
            elements.append(info_para)
            elements.append(Spacer(1, 0.1*inch))
            
            # Correct answer (for multiple choice) - only if attribute exists
            if hasattr(question, 'correct_answer') and question.correct_answer:
                correct_text = self.clean_html(question.correct_answer)
                answer_para = Paragraph(f"<b>Correct Answer:</b> {correct_text}", content_style)
                elements.append(answer_para)
                elements.append(Spacer(1, 0.1*inch))
            
            # Answer - raw from database
            if question.answer:
                elements.append(Paragraph("<b>Answer:</b>", content_style))
                # Show raw HTML/code from database
                answer_pre = Preformatted(question.answer, code_style)
                elements.append(answer_pre)
                elements.append(Spacer(1, 0.1*inch))
            
            # Explanation - only if attribute exists
            if hasattr(question, 'explanation') and question.explanation:
                explanation_text = self.clean_html(question.explanation)
                explanation_para = Paragraph(f"<b>Explanation:</b> {explanation_text}", content_style)
                elements.append(explanation_para)
                elements.append(Spacer(1, 0.1*inch))
            
            # Video link
            if question.video and question.video != 'none':
                video_para = Paragraph(f"<b>Video:</b> <link href='{question.video}'>{question.video}</link>", content_style)
                elements.append(video_para)
            
            # Add spacing between questions
            elements.append(Spacer(1, 0.3*inch))
            
            # Optional: Add page break after every few questions
            if idx % 3 == 0 and idx < questions.count():
                elements.append(PageBreak())
        
        # Build PDF
        doc.build(elements)
        
        self.stdout.write(self.style.SUCCESS(f'PDF successfully created: {output_path}'))
        self.stdout.write(self.style.SUCCESS(f'Total questions exported: {questions.count()}'))

