"""
LaTeX Question Parser for Past Papers.

This module extracts individual questions from IB past paper LaTeX files
by splitting on question markers like "1. [Maximum mark: X]".
"""

import os
import re
from pathlib import Path
from typing import List, Dict


def extract_text_from_latex(latex_path: str) -> str:
    """
    Read LaTeX file content.
    
    Args:
        latex_path: Path to the LaTeX file
        
    Returns:
        LaTeX content as a string
    """
    try:
        with open(latex_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading LaTeX file {latex_path}: {e}")
        return ""


def convert_latex_to_html(latex_content: str) -> str:
    """
    Convert basic LaTeX formatting to HTML for display.
    Preserves LaTeX math notation for MathJax.
    
    Args:
        latex_content: LaTeX content
        
    Returns:
        HTML-formatted content with LaTeX math preserved
    """
    # Keep as-is for now, frontend has MathJax
    # Just wrap in paragraph tags
    lines = latex_content.split('\n')
    html_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            # Skip LaTeX commands we don't need
            if line.startswith('\\includegraphics'):
                html_lines.append(f'<p><em>[Image: {line}]</em></p>')
            elif line.startswith('\\'):
                continue
            else:
                html_lines.append(f'<p>{line}</p>')
    
    return '\n'.join(html_lines)


def split_questions_by_markers(text: str) -> List[Dict[str, str]]:
    """
    Split LaTeX text into individual questions based on "Maximum mark:" markers.
    
    Args:
        text: Full LaTeX text
        
    Returns:
        List of dictionaries with question info
    """
    questions = []
    
    # Simpler pattern - just look for [Maximum mark: X] anywhere
    pattern = r'\[Maximum mark:\s*(\d+)\]'
    
    # Find all matches and their positions
    matches = list(re.finditer(pattern, text))
    
    if not matches:
        return []
    
    for i, match in enumerate(matches):
        max_marks = match.group(1)
        start_pos = match.end()
        
        # Skip any whitespace or \end{enumerate}
        while start_pos < len(text) and (text[start_pos].isspace() or text[start_pos:start_pos+15] == '\\end{enumerate}'):
            if text[start_pos:start_pos+15] == '\\end{enumerate}':
                start_pos += 15
            else:
                start_pos += 1
        
        # Find the end position (start of next question or end of text)
        if i < len(matches) - 1:
            end_pos = matches[i + 1].start()
            # Back up to not include the question number line before the marker
            # Look for pattern like "2. [Maximum mark:" and back up to start of line
            temp_pos = end_pos - 1
            while temp_pos > start_pos and text[temp_pos] != '\n':
                temp_pos -= 1
            if temp_pos > start_pos:
                end_pos = temp_pos
        else:
            # For last question, find \end{document} or end of file
            end_doc = text.find('\\end{document}', start_pos)
            end_pos = end_doc if end_doc != -1 else len(text)
        
        # Extract question content
        question_content = text[start_pos:end_pos].strip()
        
        # Skip if content is too short
        if len(question_content) < 10:
            continue
        
        # Clean up continuation markers
        question_content = re.sub(r'\\section\*\{\(Question \d+ continued\)\}', '', question_content)
        question_content = re.sub(r'\(This question continues on the following page\)', '', question_content)
        question_content = re.sub(r'\[0pt\]', '', question_content)
        
        # Clean leading/trailing whitespace again
        question_content = question_content.strip()
        
        questions.append({
            'question_number': i + 1,
            'max_marks': max_marks,
            'content': question_content[:2000],  # Limit for preview
            'full_content': question_content,
            'format': 'latex'
        })
    
    return questions


def parse_past_paper_latex(latex_path: str) -> List[Dict[str, str]]:
    """
    Parse a past paper LaTeX file and extract individual questions.
    
    Args:
        latex_path: Path to the LaTeX file
        
    Returns:
        List of question dictionaries
    """
    text = extract_text_from_latex(latex_path)
    if not text:
        return []
    
    questions = split_questions_by_markers(text)
    
    # Add file metadata to each question
    latex_name = Path(latex_path).stem
    for q in questions:
        q['source_file'] = latex_name
        q['source_path'] = latex_path
    
    return questions


def scan_past_papers_directory(base_dir: str) -> Dict[str, List[Dict]]:
    """
    Scan the past_papers directory and catalog all available LaTeX papers.
    
    Args:
        base_dir: Base directory containing past papers (e.g., .../past_papers/)
        
    Returns:
        Dictionary mapping subject/session to list of papers
    """
    catalog = {}
    base_path = Path(base_dir)
    
    if not base_path.exists():
        return catalog
    
    # Find all LaTeX question files
    for tex_path in base_path.rglob("*questions.tex"):
        # Get relative path from base_dir
        rel_path = tex_path.relative_to(base_path)
        
        # Extract subject and session
        parts = rel_path.parts
        if len(parts) < 2:
            continue
        
        subject = parts[0]  # e.g., "math_ai_sl"
        session = parts[1]  # e.g., "may23tz1"
        paper_name = tex_path.stem  # e.g., "paper1_questions"
        
        key = f"{subject}/{session}"
        
        if key not in catalog:
            catalog[key] = {}
        
        # Parse questions from this LaTeX file
        questions = parse_past_paper_latex(str(tex_path))
        catalog[key][paper_name] = questions
    
    return catalog


def get_available_papers(base_dir: str) -> List[Dict[str, str]]:
    """
    Get a list of available LaTeX papers for the dropdown.
    
    Returns:
        List of dictionaries with paper info
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
        
        # Format session name
        session_formatted = format_session_name(session)
        
        for paper_name in paper_dict.keys():
            # Extract paper number
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
