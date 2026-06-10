"""
Generate similar IB Math questions using RAG.

This script:
1. Takes a question or topic as input
2. Finds similar questions from the vector database
3. Uses GPT-4 to generate a new similar question

Usage:
    python generate_question.py "What is the probability of rolling a 6?"
    python generate_question.py --topic "normal distribution"
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_PATH)

# ChromaDB path
CHROMA_DIR = Path(__file__).parent / "chroma_db"

# System prompt for question generation
SYSTEM_PROMPT = """You are an expert IB Mathematics exam question writer. Your task is to generate new exam questions that are similar in style, difficulty, and format to existing IB Math questions.

Guidelines:
1. Match the IB Math style exactly - use proper mathematical notation
2. Include realistic context/scenarios like real IB questions
3. Specify the maximum marks for each question part
4. Make the question challenging but fair for IB students
5. Include multiple parts (a), (b), (c) etc. when appropriate
6. The difficulty should match the examples provided

Format your response as:
QUESTION [Maximum mark: X]
<question text with parts labeled (a), (b), etc.>

SUGGESTED MARK SCHEME:
<brief marking guide>
"""

USER_PROMPT_TEMPLATE = """Based on these similar IB Math questions from past papers:

{context}

---

Generate a NEW, ORIGINAL question that is similar in style and difficulty to the examples above.

Topic/Focus: {topic}

Requirements:
- The question must be DIFFERENT from the examples (not just changing numbers)
- Maintain the same level of complexity and IB style
- Include appropriate context/real-world application if the examples have it
"""


def load_vectorstore():
    """Load the ChromaDB vector store."""
    if not CHROMA_DIR.exists():
        print("ERROR: ChromaDB not found!")
        print("Run 'python process_pdfs.py' first to create the database.")
        sys.exit(1)
    
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name="ib_questions"
    )
    
    return vectorstore


def find_similar_questions(vectorstore, query: str, k: int = 3):
    """Find similar questions from the database."""
    results = vectorstore.similarity_search(query, k=k)
    return results


def generate_similar_question(similar_docs: list, topic: str, model: str = "gpt-4o") -> str:
    """
    Generate a new question based on similar examples.
    """
    # Prepare context from similar questions
    context_parts = []
    for i, doc in enumerate(similar_docs, 1):
        meta = doc.metadata
        context_parts.append(f"""
--- Example {i} ({meta['subject']}, {meta['session']}, Question {meta['question_number']}) ---
{doc.page_content}
""")
    
    context = "\n".join(context_parts)
    
    # Create the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT_TEMPLATE),
    ])
    
    # Initialize the LLM
    llm = ChatOpenAI(
        model=model,
        temperature=0.7,  # Some creativity for varied questions
    )
    
    # Generate
    chain = prompt | llm
    response = chain.invoke({
        "context": context,
        "topic": topic,
    })
    
    return response.content


def main():
    parser = argparse.ArgumentParser(description="Generate similar IB Math questions")
    parser.add_argument("query", nargs="?", help="Question or topic to find similar questions for")
    parser.add_argument("--topic", "-t", help="Specific topic for generation")
    parser.add_argument("--num-examples", "-n", type=int, default=3, help="Number of similar examples to use")
    parser.add_argument("--model", "-m", default="gpt-4o", help="OpenAI model to use")
    
    args = parser.parse_args()
    
    # Determine query and topic
    query = args.query or args.topic
    topic = args.topic or args.query
    
    if not query:
        # Interactive mode
        print("=" * 60)
        print("IB Math Question Generator")
        print("=" * 60)
        query = input("\nEnter a topic or question to find similar examples: ").strip()
        topic = query
    
    if not query:
        print("ERROR: Please provide a topic or question")
        sys.exit(1)
    
    print(f"\n🔍 Searching for questions related to: '{query}'")
    
    # Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found")
        sys.exit(1)
    
    # Load vectorstore
    vectorstore = load_vectorstore()
    
    # Find similar questions
    similar_docs = find_similar_questions(vectorstore, query, k=args.num_examples)
    
    if not similar_docs:
        print("No similar questions found in the database.")
        sys.exit(1)
    
    print(f"\n📚 Found {len(similar_docs)} similar questions:")
    for i, doc in enumerate(similar_docs, 1):
        meta = doc.metadata
        preview = doc.page_content[:150].replace('\n', ' ')
        print(f"  {i}. [{meta['subject']}/{meta['session']}] Q{meta['question_number']}: {preview}...")
    
    print(f"\n🤖 Generating new question using {args.model}...")
    print("-" * 60)
    
    # Generate new question
    new_question = generate_similar_question(similar_docs, topic, args.model)
    
    print("\n" + "=" * 60)
    print("GENERATED QUESTION")
    print("=" * 60)
    print(new_question)
    print("=" * 60)
    
    return new_question


if __name__ == "__main__":
    main()

















