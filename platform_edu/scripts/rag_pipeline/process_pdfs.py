"""
Process IB Math PDFs and store in ChromaDB vector database.

This script:
1. Extracts text from question PDFs and mark scheme PDFs
2. Splits into individual questions
3. Pairs questions with their mark schemes
4. Creates embeddings and stores in ChromaDB

Usage:
    python process_pdfs.py
"""

import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

import fitz  # PyMuPDF
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Load environment variables from .env file
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_PATH)

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
PDF_DIR = BASE_DIR / "static/website/images/pdfs/past_papers"
CHROMA_DIR = BASE_DIR / "scripts/rag_pipeline/chroma_db"

# Ensure ChromaDB directory exists
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    if not pdf_path.exists():
        print(f"  WARNING: PDF not found: {pdf_path}")
        return ""
    
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    doc.close()
    return text


def split_into_questions(text: str) -> list[dict]:
    """
    Split extracted text into individual questions.
    Returns list of dicts with question number and text.
    """
    questions = []
    
    # Pattern for IB questions: number followed by period or [Maximum mark: X]
    # Handles both "1." and "1. [Maximum mark: 6]" formats
    pattern = r'\n(\d+)\.\s*(?:\[Maximum mark:\s*(\d+)\])?\s*'
    
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    
    if not matches:
        # If no matches, return the whole text as one chunk
        return [{"number": "1", "max_mark": "?", "text": text.strip()}]
    
    for i, match in enumerate(matches):
        q_num = match.group(1)
        max_mark = match.group(2) if match.group(2) else "?"
        start = match.start()
        
        # End is either next question or end of text
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)
        
        q_text = text[start:end].strip()
        
        # Skip if too short (probably header/footer noise)
        if len(q_text) > 50:
            questions.append({
                "number": q_num,
                "max_mark": max_mark,
                "text": q_text
            })
    
    return questions


def extract_markscheme_for_question(ms_text: str, q_num: str) -> str:
    """
    Extract the mark scheme section for a specific question number.
    """
    # Pattern to find question section in mark scheme
    pattern = rf'\n{q_num}\.\s+'
    
    matches = list(re.finditer(pattern, ms_text))
    
    if not matches:
        return ""
    
    start = matches[0].start()
    
    # Find next question number
    next_q = int(q_num) + 1
    next_pattern = rf'\n{next_q}\.\s+'
    next_match = re.search(next_pattern, ms_text[start + 10:])
    
    if next_match:
        end = start + 10 + next_match.start()
    else:
        # Take a reasonable chunk if no next question found
        end = min(start + 3000, len(ms_text))
    
    return ms_text[start:end].strip()


def process_exam_paper(questions_pdf: Path, markscheme_pdf: Path, metadata: dict) -> list[Document]:
    """
    Process a single exam paper (questions + mark scheme) into documents.
    """
    documents = []
    
    print(f"  Processing: {questions_pdf.name}")
    
    # Extract text
    q_text = extract_text_from_pdf(questions_pdf)
    ms_text = extract_text_from_pdf(markscheme_pdf) if markscheme_pdf.exists() else ""
    
    if not q_text:
        print(f"    WARNING: No text extracted from {questions_pdf}")
        return documents
    
    # Split into questions
    questions = split_into_questions(q_text)
    print(f"    Found {len(questions)} questions")
    
    for q in questions:
        # Get corresponding mark scheme
        ms = extract_markscheme_for_question(ms_text, q["number"]) if ms_text else ""
        
        # Create combined content
        content = f"""QUESTION {q['number']} [Maximum mark: {q['max_mark']}]

{q['text']}

--- MARK SCHEME ---
{ms if ms else 'Mark scheme not available'}
"""
        
        # Create document with metadata
        doc = Document(
            page_content=content,
            metadata={
                **metadata,
                "question_number": q["number"],
                "max_mark": q["max_mark"],
            }
        )
        documents.append(doc)
    
    return documents


def discover_pdfs(pdf_dir: Path) -> list[dict]:
    """
    Discover all PDF pairs (questions + mark schemes) in the directory.
    Returns list of dicts with paths and metadata.
    """
    papers = []
    
    # Walk through the directory structure
    # Expected: pdf_dir/subject/session/files.pdf
    for subject_dir in pdf_dir.iterdir():
        if not subject_dir.is_dir():
            continue
        
        subject = subject_dir.name  # e.g., "math_ai_sl"
        
        for session_dir in subject_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            session = session_dir.name  # e.g., "may23tz1"
            
            # Find paper pairs
            for pdf_file in session_dir.glob("*_questions.pdf"):
                paper_name = pdf_file.name.replace("_questions.pdf", "")
                ms_file = session_dir / f"{paper_name}_answers.pdf"
                
                papers.append({
                    "questions_pdf": pdf_file,
                    "markscheme_pdf": ms_file,
                    "metadata": {
                        "subject": subject,
                        "session": session,
                        "paper": paper_name,
                        "source_file": pdf_file.name,
                    }
                })
    
    return papers


def main():
    print("=" * 70)
    print("RAG PIPELINE - Processing IB Math PDFs")
    print("=" * 70)
    
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found in environment")
        print(f"Make sure it's set in: {ENV_PATH}")
        return
    
    print(f"\n[1/4] Discovering PDFs in {PDF_DIR}...")
    papers = discover_pdfs(PDF_DIR)
    
    if not papers:
        print("  No PDFs found!")
        print(f"  Expected structure: {PDF_DIR}/subject/session/paperX_questions.pdf")
        return
    
    print(f"  Found {len(papers)} exam papers:")
    for p in papers:
        print(f"    - {p['metadata']['subject']}/{p['metadata']['session']}/{p['metadata']['paper']}")
    
    print(f"\n[2/4] Processing PDFs and extracting questions...")
    all_documents = []
    
    for paper in papers:
        docs = process_exam_paper(
            paper["questions_pdf"],
            paper["markscheme_pdf"],
            paper["metadata"]
        )
        all_documents.extend(docs)
    
    print(f"\n  Total documents created: {len(all_documents)}")
    
    if not all_documents:
        print("  ERROR: No documents created!")
        return
    
    print(f"\n[3/4] Creating embeddings and storing in ChromaDB...")
    print(f"  Database location: {CHROMA_DIR}")
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",  # Cheap and effective
    )
    
    # Create or update ChromaDB
    vectorstore = Chroma.from_documents(
        documents=all_documents,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="ib_questions"
    )
    
    print(f"  Stored {len(all_documents)} documents in ChromaDB")
    
    print(f"\n[4/4] Testing retrieval...")
    # Test query
    test_query = "probability statistics normal distribution"
    results = vectorstore.similarity_search(test_query, k=2)
    
    print(f"  Test query: '{test_query}'")
    print(f"  Found {len(results)} similar questions:")
    for i, doc in enumerate(results, 1):
        preview = doc.page_content[:200].replace('\n', ' ')
        print(f"    {i}. [{doc.metadata['subject']}/{doc.metadata['session']}] Q{doc.metadata['question_number']}")
        print(f"       {preview}...")
    
    print("\n" + "=" * 70)
    print("SUCCESS! RAG pipeline ready.")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"1. Run 'python generate_question.py' to test question generation")
    print(f"2. Integrate with Django views")
    print("=" * 70)


if __name__ == "__main__":
    main()

















