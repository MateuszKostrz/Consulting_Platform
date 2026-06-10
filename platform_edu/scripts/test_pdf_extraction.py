"""
Test script to verify PDF extraction quality for IB Math papers.
Run this to see how well we can extract and split questions from your PDFs.

Usage:
    python test_pdf_extraction.py
"""

import re
import sys
from pathlib import Path

# Check if pymupdf is installed
try:
    import fitz  # PyMuPDF
except ImportError:
    print("=" * 60)
    print("PyMuPDF not installed. Please run:")
    print("    pip install pymupdf")
    print("=" * 60)
    sys.exit(1)


# Path to test PDF
PDF_PATH = Path(__file__).parent.parent / "static/website/images/pdfs/past_papers/math_ai_sl/may23tz1/paper1_questions.pdf"
MS_PATH = Path(__file__).parent.parent / "static/website/images/pdfs/past_papers/math_ai_sl/may23tz1/paper1_answers.pdf"


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        sys.exit(1)
    
    doc = fitz.open(pdf_path)
    text = ""
    
    for page_num, page in enumerate(doc, 1):
        page_text = page.get_text()
        text += f"\n--- PAGE {page_num} ---\n"
        text += page_text
    
    doc.close()
    return text


def split_into_questions(text: str) -> list[dict]:
    """
    Attempt to split extracted text into individual questions.
    IB papers typically have "Question 1", "Question 2", etc. or just "1.", "2.", etc.
    """
    # Common patterns for IB math papers
    # Pattern 1: "1." at start of line (most common)
    # Pattern 2: "Question 1" 
    
    questions = []
    
    # Try to split by question numbers (1., 2., 3., etc.)
    # This pattern looks for a number followed by a period at the start of a line
    pattern = r'\n(\d+)\.\s+'
    
    # Find all question starts
    matches = list(re.finditer(pattern, text))
    
    if not matches:
        print("WARNING: Could not detect question boundaries with standard pattern.")
        print("The PDF might use a different format.")
        return []
    
    for i, match in enumerate(matches):
        q_num = match.group(1)
        start = match.start()
        
        # End is either the next question or end of text
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)
        
        q_text = text[start:end].strip()
        
        questions.append({
            "number": q_num,
            "text": q_text,
            "char_count": len(q_text)
        })
    
    return questions


def main():
    print("=" * 70)
    print("PDF EXTRACTION TEST - IB Math AI SL May 2023 TZ1 Paper 1")
    print("=" * 70)
    
    # Step 1: Extract raw text
    print("\n[1/4] Extracting text from questions PDF...")
    questions_text = extract_text_from_pdf(PDF_PATH)
    print(f"      Extracted {len(questions_text):,} characters")
    
    # Step 2: Show sample of raw text
    print("\n[2/4] Sample of extracted text (first 2000 chars):")
    print("-" * 50)
    print(questions_text[:2000])
    print("-" * 50)
    
    # Step 3: Try to split into questions
    print("\n[3/4] Attempting to split into individual questions...")
    questions = split_into_questions(questions_text)
    
    if questions:
        print(f"      Found {len(questions)} questions!\n")
        
        for q in questions:
            print(f"      Question {q['number']}: {q['char_count']} chars")
            # Show first 200 chars of each question
            preview = q['text'][:200].replace('\n', ' ')
            print(f"         Preview: {preview}...")
            print()
    else:
        print("      Could not automatically split questions.")
        print("      You may need to adjust the splitting logic.")
    
    # Step 4: Check mark scheme
    print("\n[4/4] Checking mark scheme PDF...")
    if MS_PATH.exists():
        ms_text = extract_text_from_pdf(MS_PATH)
        print(f"      Mark scheme: {len(ms_text):,} characters extracted")
        print("\n      Mark scheme sample (first 1000 chars):")
        print("-" * 50)
        print(ms_text[:1000])
        print("-" * 50)
    else:
        print(f"      Mark scheme not found at {MS_PATH}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Questions PDF readable: Yes")
    print(f"✓ Total text extracted: {len(questions_text):,} characters")
    print(f"✓ Questions detected: {len(questions)}")
    print(f"✓ Mark scheme PDF readable: {'Yes' if MS_PATH.exists() else 'No'}")
    print("\nNEXT STEPS:")
    print("1. Review the extracted text above")
    print("2. Check if math symbols (∫, Σ, √, fractions) extracted correctly")
    print("3. Verify question boundaries are detected properly")
    print("4. If issues, we'll adjust the extraction approach")
    print("=" * 70)


if __name__ == "__main__":
    main()

















