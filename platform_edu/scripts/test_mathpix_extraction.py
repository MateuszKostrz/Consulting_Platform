"""
Test script using Mathpix API for high-quality math extraction.
Mathpix converts PDFs to clean LaTeX/Markdown with proper math notation.

Usage:
    1. Set your Mathpix credentials below (or as environment variables)
    2. Run: python test_mathpix_extraction.py
"""

import os
import re
import sys
import json
import time
import requests
from pathlib import Path

# ============================================================
# MATHPIX CREDENTIALS - Set these or use environment variables
# ============================================================
# Get your credentials from: https://mathpix.com/dashboard/api-keys
MATHPIX_APP_ID = os.environ.get("MATHPIX_APP_ID", "YOUR_APP_ID_HERE")
MATHPIX_APP_KEY = os.environ.get("MATHPIX_APP_KEY", "YOUR_APP_KEY_HERE")
# ============================================================

# Path to test PDF
PDF_PATH = Path(__file__).parent.parent / "static/website/images/pdfs/past_papers/math_ai_sl/may23tz1/paper1_questions.pdf"

# Output directory for extracted content
OUTPUT_DIR = Path(__file__).parent / "mathpix_output"


def check_credentials():
    """Verify Mathpix credentials are set."""
    if MATHPIX_APP_ID == "YOUR_APP_ID_HERE" or MATHPIX_APP_KEY == "YOUR_APP_KEY_HERE":
        print("=" * 60)
        print("ERROR: Mathpix credentials not set!")
        print()
        print("Please either:")
        print("1. Edit this file and set MATHPIX_APP_ID and MATHPIX_APP_KEY")
        print("2. Or set environment variables:")
        print("   export MATHPIX_APP_ID='your_app_id'")
        print("   export MATHPIX_APP_KEY='your_app_key'")
        print()
        print("Get your credentials from: https://mathpix.com/dashboard/api-keys")
        print("=" * 60)
        sys.exit(1)


def convert_pdf_with_mathpix(pdf_path: Path) -> dict:
    """
    Convert PDF to Markdown using Mathpix API.
    Returns the conversion result with extracted text.
    """
    print(f"   Uploading {pdf_path.name} to Mathpix...")
    
    # Step 1: Upload the PDF and start conversion
    url = "https://api.mathpix.com/v3/pdf"
    
    headers = {
        "app_id": MATHPIX_APP_ID,
        "app_key": MATHPIX_APP_KEY,
    }
    
    options = {
        "conversion_formats": {"md": True},  # Get Markdown output
        "math_inline_delimiters": ["$", "$"],
        "math_display_delimiters": ["$$", "$$"],
    }
    
    with open(pdf_path, "rb") as f:
        files = {
            "file": (pdf_path.name, f, "application/pdf"),
            "options_json": (None, json.dumps(options), "application/json"),
        }
        response = requests.post(url, headers=headers, files=files)
    
    if response.status_code != 200:
        print(f"   ERROR: Upload failed with status {response.status_code}")
        print(f"   Response: {response.text}")
        return None
    
    result = response.json()
    pdf_id = result.get("pdf_id")
    print(f"   PDF ID: {pdf_id}")
    
    # Step 2: Poll for completion
    print("   Waiting for conversion to complete...")
    status_url = f"https://api.mathpix.com/v3/pdf/{pdf_id}"
    
    max_attempts = 60  # Wait up to 5 minutes
    for attempt in range(max_attempts):
        response = requests.get(status_url, headers=headers)
        status_data = response.json()
        status = status_data.get("status")
        
        if status == "completed":
            print("   Conversion completed!")
            break
        elif status == "error":
            print(f"   ERROR: Conversion failed - {status_data}")
            return None
        else:
            # Show progress
            percent = status_data.get("percent_done", 0)
            print(f"   Status: {status} ({percent}% done)...")
            time.sleep(5)
    else:
        print("   ERROR: Conversion timed out")
        return None
    
    # Step 3: Download the Markdown result
    md_url = f"https://api.mathpix.com/v3/pdf/{pdf_id}.md"
    response = requests.get(md_url, headers=headers)
    
    if response.status_code != 200:
        print(f"   ERROR: Failed to download Markdown")
        return None
    
    return {
        "pdf_id": pdf_id,
        "markdown": response.text,
        "status_data": status_data
    }


def split_into_questions(markdown_text: str) -> list[dict]:
    """
    Split Mathpix markdown output into individual questions.
    """
    questions = []
    
    # Pattern for IB questions: "1. [Maximum mark: X]" or just "1."
    # In markdown, questions might be formatted as headers or bold
    pattern = r'\n(\d+)\.\s*\[Maximum mark:\s*(\d+)\]'
    
    matches = list(re.finditer(pattern, markdown_text, re.IGNORECASE))
    
    if not matches:
        # Try simpler pattern
        pattern = r'\n(\d+)\.\s+'
        matches = list(re.finditer(pattern, markdown_text))
    
    if not matches:
        print("   WARNING: Could not detect question boundaries")
        return []
    
    for i, match in enumerate(matches):
        q_num = match.group(1)
        max_mark = match.group(2) if len(match.groups()) > 1 else "?"
        start = match.start()
        
        # End is either next question or end of text
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(markdown_text)
        
        q_text = markdown_text[start:end].strip()
        
        questions.append({
            "number": q_num,
            "max_mark": max_mark,
            "text": q_text,
            "char_count": len(q_text)
        })
    
    return questions


def main():
    print("=" * 70)
    print("MATHPIX EXTRACTION TEST - IB Math AI SL May 2023 TZ1 Paper 1")
    print("=" * 70)
    
    # Check credentials
    check_credentials()
    
    # Check PDF exists
    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}")
        sys.exit(1)
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Step 1: Convert with Mathpix
    print("\n[1/3] Converting PDF with Mathpix API...")
    result = convert_pdf_with_mathpix(PDF_PATH)
    
    if not result:
        print("Conversion failed!")
        sys.exit(1)
    
    markdown = result["markdown"]
    
    # Save the raw markdown
    output_file = OUTPUT_DIR / "paper1_questions.md"
    with open(output_file, "w") as f:
        f.write(markdown)
    print(f"   Saved to: {output_file}")
    
    # Step 2: Show sample
    print("\n[2/3] Sample of extracted Markdown (first 3000 chars):")
    print("-" * 50)
    print(markdown[:3000])
    print("-" * 50)
    
    # Step 3: Split into questions
    print("\n[3/3] Splitting into individual questions...")
    questions = split_into_questions(markdown)
    
    if questions:
        print(f"   Found {len(questions)} questions!\n")
        
        for q in questions[:5]:  # Show first 5
            print(f"   Question {q['number']} [Max mark: {q['max_mark']}]: {q['char_count']} chars")
            preview = q['text'][:300].replace('\n', ' ')
            print(f"      Preview: {preview}...")
            print()
        
        if len(questions) > 5:
            print(f"   ... and {len(questions) - 5} more questions")
    
    # Save questions as JSON
    questions_file = OUTPUT_DIR / "paper1_questions.json"
    with open(questions_file, "w") as f:
        json.dump(questions, f, indent=2)
    print(f"\n   Saved questions to: {questions_file}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Mathpix conversion: Success")
    print(f"✓ Markdown extracted: {len(markdown):,} characters")
    print(f"✓ Questions detected: {len(questions)}")
    print(f"✓ Output saved to: {OUTPUT_DIR}")
    print()
    print("COMPARE: The math should now look like proper LaTeX:")
    print("  Before (PyMuPDF): y x    1 2 5 2")
    print("  After (Mathpix):  $y = \\frac{1}{2}x + \\frac{5}{2}$")
    print("=" * 70)


if __name__ == "__main__":
    main()

















