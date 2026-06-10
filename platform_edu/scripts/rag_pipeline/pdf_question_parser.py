"""
PDF Question Parser for Past Papers.

This module extracts individual questions from IB past paper PDFs
by splitting on "Maximum mark:" markers.
"""

import os
import re
from pathlib import Path
from typing import List, Dict
import PyPDF2


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""


def split_questions_by_max_mark(text: str) -> List[Dict[str, str]]:
    """
    Split PDF text into individual questions based on "Maximum mark:" marker.
    
    Args:
        text: Full text extracted from PDF
        
    Returns:
        List of dictionaries with question info
    """
    questions = []
    
    # Split by "Maximum mark:" (case insensitive)
    # Pattern matches "Maximum mark:" or "Maximum Mark:" etc.
    pattern = r'(?i)maximum\s+mark\s*:\s*\[?(\d+)\]?'
    
    # Find all matches and their positions
    matches = list(re.finditer(pattern, text))
    
    if not matches:
        # If no "Maximum mark:" found, return the whole text as one question
        return [{
            'question_number': 1,
            'max_marks': 'Unknown',
            'content': text.strip()
        }]
    
    for i, match in enumerate(matches):
        max_marks = match.group(1)
        start_pos = match.end()
        
        # Find the end position (start of next question or end of text)
        if i < len(matches) - 1:
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(text)
        
        # Extract question content
        question_content = text[start_pos:end_pos].strip()
        
        # Skip if content is too short (likely not a real question)
        if len(question_content) < 20:
            continue
        
        questions.append({
            'question_number': i + 1,
            'max_marks': max_marks,
            'content': question_content[:2000],  # Limit to 2000 chars for preview
            'full_content': question_content
        })
    
    return questions


def parse_past_paper_pdf(pdf_path: str) -> List[Dict[str, str]]:
    """
    Parse a past paper PDF and extract individual questions.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of question dictionaries
    """
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return []
    
    questions = split_questions_by_max_mark(text)
    
    # Add file metadata to each question
    pdf_name = Path(pdf_path).stem
    for q in questions:
        q['source_file'] = pdf_name
        q['source_path'] = pdf_path
    
    return questions


def scan_past_papers_directory(base_dir: str) -> Dict[str, List[Dict]]:
    """
    Scan the past_papers directory and catalog all available papers.
    
    Args:
        base_dir: Base directory containing past papers (e.g., .../past_papers/)
        
    Returns:
        Dictionary mapping subject/session to list of papers
        {
            'math_ai_sl/may23tz1': {
                'paper1_questions': [...questions...],
                'paper2_questions': [...questions...],
            }
        }
    """
    catalog = {}
    base_path = Path(base_dir)
    
    if not base_path.exists():
        return catalog
    
    # Find all question PDFs (not answers)
    for pdf_path in base_path.rglob("*questions.pdf"):
        # Get relative path from base_dir
        rel_path = pdf_path.relative_to(base_path)
        
        # Extract subject and session (e.g., math_ai_sl/may23tz1)
        parts = rel_path.parts
        if len(parts) < 2:
            continue
        
        subject = parts[0]  # e.g., "math_ai_sl"
        session = parts[1]  # e.g., "may23tz1"
        paper_name = pdf_path.stem  # e.g., "paper1_questions"
        
        key = f"{subject}/{session}"
        
        if key not in catalog:
            catalog[key] = {}
        
        # Parse questions from this PDF
        questions = parse_past_paper_pdf(str(pdf_path))
        catalog[key][paper_name] = questions
    
    return catalog


def get_available_papers(base_dir: str) -> List[Dict[str, str]]:
    """
    Get a list of available papers for the dropdown.
    
    Returns:
        List of dictionaries with paper info
        [
            {'value': 'math_ai_sl/may23tz1/paper1_questions', 'label': 'Math AI SL - May 2023 TZ1 - Paper 1'},
            ...
        ]
    """
    catalog = scan_past_papers_directory(base_dir)
    papers = []
    
    # Subject name mapping
    subject_names = {
        'math_ai_sl': 'Math AI SL',
        'math_ai_hl': 'Math AI HL',
        'math_aa_sl': 'Math AA SL',
        'math_aa_hl': 'Math AA HL',
        'physics_sl': 'Physics SL',
        'physics_hl': 'Physics HL',
        'chemistry_sl': 'Chemistry SL',
        'chemistry_hl': 'Chemistry HL',
        'biology_sl': 'Biology SL',
        'biology_hl': 'Biology HL',
    }
    
    for key, paper_dict in catalog.items():
        subject, session = key.split('/')
        subject_name = subject_names.get(subject, subject.replace('_', ' ').title())
        
        # Format session name (e.g., may23tz1 -> May 2023 TZ1)
        session_formatted = format_session_name(session)
        
        for paper_name in paper_dict.keys():
            # Extract paper number (e.g., paper1_questions -> Paper 1)
            paper_num = paper_name.replace('_questions', '').replace('paper', 'Paper ')
            
            papers.append({
                'value': f"{key}/{paper_name}",
                'label': f"{subject_name} - {session_formatted} - {paper_num}",
                'subject': subject,
                'session': session,
                'paper': paper_name
            })
    
    return sorted(papers, key=lambda x: x['label'])


def format_session_name(session: str) -> str:
    """
    Format session code to readable name.
    e.g., may23tz1 -> May 2023 TZ1
    """
    # Extract month, year, and timezone
    match = re.match(r'([a-z]+)(\d{2})(tz\d)?', session.lower())
    if match:
        month_code, year, tz = match.groups()
        
        months = {
            'may': 'May',
            'nov': 'November',
            'specimen': 'Specimen'
        }
        
        month = months.get(month_code, month_code.capitalize())
        year_full = f"20{year}"
        tz_str = f" {tz.upper()}" if tz else ""
        
        return f"{month} {year_full}{tz_str}"
    
    return session.upper()
