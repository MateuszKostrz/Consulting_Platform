"""
Question Generator Module for Django Integration.

This module provides functions to generate similar IB questions
using RAG (Retrieval Augmented Generation).
"""

import os
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
SYSTEM_PROMPT = """You are an expert IB Mathematics exam question writer. Your task is to generate new exam questions that are similar in style and test the same mathematical concepts, but with CREATIVE and DIFFERENT scenarios.

Guidelines:
1. Match the IB Math style exactly - use proper mathematical notation with LaTeX (use \\( and \\) for inline math, \\[ and \\] for display math)
2. BE CREATIVE with the context/scenario - use completely different real-world situations (e.g., if original is about wire length, use something like population growth, chemical concentration, sports statistics, etc.)
3. Test the SAME mathematical skills but with fresh, engaging contexts
4. Keep mark allocations REALISTIC and MODEST:
   - Simple recall/state questions: 1-2 marks
   - Standard calculations: 2-3 marks  
   - Multi-step problems: 3-4 marks
   - Total question should typically be 5-8 marks (not more than 10)
5. Include 2-4 parts maximum, not too many sub-questions

CRITICAL: If the user provides ADDITIONAL REQUIREMENTS in the prompt, you MUST follow them exactly. These requirements override the general guidelines above and are mandatory.

CRITICAL - You MUST format your response using this exact HTML structure:

<p><strong>[Maximum mark: X]</strong></p>
<p>[Introduction/context paragraph - BE CREATIVE with a fresh scenario!]</p>
<p class="question"><strong>(a)</strong> [Part a question text] <strong>[Y marks]</strong></p>
<p class="question"><strong>(b)</strong> [Part b question text] <strong>[Y marks]</strong></p>
<p class="question"><strong>(c)</strong> [Part c question text] <strong>[Y marks]</strong></p>

Rules for formatting:
- ONLY sub-question paragraphs (a), (b), (c), etc. should have class="question"
- The maximum mark line and context/intro paragraphs should NOT have the class
- Part labels like (a), (b), (c) must be wrapped in <strong> tags
- Mark allocations like [1 mark] or [2 marks] must be wrapped in <strong> tags at the end
- Use \\( and \\) for inline LaTeX math (e.g., \\(x^2 + 5x + 6\\))
- Use \\[ and \\] for display/block LaTeX math
- Do NOT use markdown formatting - only HTML
- Do NOT include ```html or any code fences
"""

USER_PROMPT_TEMPLATE = """Here is the original question the student is studying:

ORIGINAL QUESTION:
{original_question}

ORIGINAL EXPLANATION/ANSWER:
{original_answer}

---

Here are similar questions from past IB papers for reference style:

{context}

---

{custom_instructions}

Generate a NEW, CREATIVE question that:
1. Tests the SAME mathematical concepts/skills as the original
2. Uses a COMPLETELY DIFFERENT real-world scenario (e.g., sports, cooking, travel, business, nature, technology, music, art, etc.)
3. Has REALISTIC mark allocations (total 5-8 marks, individual parts 1-3 marks each)
4. Is fresh and engaging - avoid being too similar to the original

Be imaginative with the context! If the original uses measurement, you could use temperature, speed, money, etc. Make it interesting for students.

IMPORTANT: Output ONLY the HTML-formatted question. Only sub-questions (a), (b), (c) get class="question". Do not include any explanation or markdown.
"""


class QuestionGenerator:
    """Class to handle question generation using RAG."""
    
    def __init__(self):
        """Initialize the question generator."""
        self.vectorstore = None
        self.embeddings = None
        self.llm = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of components."""
        if self._initialized:
            return
        
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        if CHROMA_DIR.exists():
            self.vectorstore = Chroma(
                persist_directory=str(CHROMA_DIR),
                embedding_function=self.embeddings,
                collection_name="ib_questions"
            )
        
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.9,  # Higher temperature for more creative variations
        )
        
        self._initialized = True
    
    def generate_similar_question(
        self,
        original_question: str,
        original_answer: str,
        subject: str = "",
        topic: str = "",
        temperature: float = 0.9,
        custom_instructions: str = "",
        num_examples: int = 2
    ) -> dict:
        """
        Generate a similar question based on the original question and answer.
        
        Args:
            original_question: The HTML content of the original question
            original_answer: The HTML content of the explanation/answer
            subject: Subject name for better retrieval (e.g., "Biology SL", "Physics HL")
            topic: Optional topic hint for better retrieval (e.g., "Cell biology")
            temperature: AI temperature (0.0-2.0, default 0.9). Higher = more creative
            custom_instructions: Additional instructions for the AI
            num_examples: Number of similar examples to retrieve
            
        Returns:
            dict with 'success', 'question', and optional 'error'
        """
        try:
            self._ensure_initialized()
            
            # Clean HTML for search (remove tags for better embedding match)
            import re
            clean_question = re.sub(r'<[^>]+>', ' ', original_question)
            clean_answer = re.sub(r'<[^>]+>', ' ', original_answer)
            
            # Create search query from subject, topic, and question content
            # Prioritize subject to ensure we search in the correct subject area
            search_parts = []
            if subject:
                search_parts.append(subject)
            if topic:
                search_parts.append(topic)
            search_parts.append(clean_question[:500])
            search_query = " ".join(search_parts)
            
            # Find similar questions from vector store (if available)
            context = ""
            if self.vectorstore:
                similar_docs = self.vectorstore.similarity_search(search_query, k=num_examples)
                
                context_parts = []
                for i, doc in enumerate(similar_docs, 1):
                    meta = doc.metadata
                    context_parts.append(f"""
--- Reference Example {i} ({meta.get('subject', 'IB Math')}, {meta.get('session', '')}) ---
{doc.page_content[:1500]}
""")
                context = "\n".join(context_parts)
            else:
                context = "(No additional reference examples available)"
            
            # Format custom instructions if provided
            custom_instructions_formatted = ""
            if custom_instructions:
                custom_instructions_formatted = f"""
*** CRITICAL REQUIREMENTS - YOU MUST FOLLOW THESE ***
{custom_instructions}
*** END CRITICAL REQUIREMENTS ***

"""
                print(f"DEBUG: Custom instructions provided: {custom_instructions}")
            
            # Create LLM with specified temperature
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=temperature,
            )
            
            # Create the prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", USER_PROMPT_TEMPLATE),
            ])
            
            # Generate
            chain = prompt | llm
            response = chain.invoke({
                "original_question": clean_question[:2000],
                "original_answer": clean_answer[:2000],
                "context": context,
                "custom_instructions": custom_instructions_formatted,
            })
            
            return {
                "success": True,
                "question": response.content,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# Global instance for reuse
_generator = None

def get_generator() -> QuestionGenerator:
    """Get or create the global question generator instance."""
    global _generator
    if _generator is None:
        _generator = QuestionGenerator()
    return _generator


def generate_similar_question(
    original_question: str,
    original_answer: str,
    subject: str = "",
    topic: str = "",
    temperature: float = 0.9,
    custom_instructions: str = ""
) -> dict:
    """
    Convenience function to generate a similar question.
    
    Args:
        original_question: The HTML content of the original question
        original_answer: The HTML content of the explanation/answer
        subject: Subject name (e.g., "Biology SL", "Physics HL")
        topic: Optional topic hint (e.g., "Cell biology")
        temperature: AI temperature (0.0-2.0, default 0.9). Higher = more creative
        custom_instructions: Additional instructions for the AI
        
    Returns:
        dict with 'success', 'question', and optional 'error'
    """
    generator = get_generator()
    return generator.generate_similar_question(
        original_question=original_question,
        original_answer=original_answer,
        subject=subject,
        topic=topic,
        temperature=temperature,
        custom_instructions=custom_instructions,
    )


# System prompt for explanation generation
EXPLANATION_SYSTEM_PROMPT = """You are an expert IB tutor providing detailed, step-by-step explanations for exam questions.

Your explanations should:
1. Break down the solution into clear, logical steps
2. Explain WHY each step is taken (not just HOW)
3. Use proper mathematical notation with LaTeX
4. Include key concepts and formulas used
5. Be thorough but concise - focus on understanding
6. Follow IB marking scheme style where appropriate

CRITICAL - You MUST format your response using this exact HTML structure:

<p class="answers-ms"><strong>a)</strong> [Start with explanation for part a]</p>
<p>[Additional explanation text]</p>
<p><span class="math">\\[ [Display math equations go here] \\]</span></p>
<p>[More explanation with inline math using \\( x^2 \\)]</p>

<p class="answers-ms"><strong>b)</strong> [Start with explanation for part b]</p>
<p>[Continue with steps...]</p>
<p><span class="math">\\[ [More equations] \\]</span></p>

FORMATTING RULES:
- Each answer part (a, b, c, etc.) starts with: <p class="answers-ms"><strong>a)</strong>
- Regular paragraph text uses: <p>[text]</p>
- Inline math uses: \\( equation \\) directly in paragraphs
- Display/block math uses: <p><span class="math">\\[ equation \\]</span></p>
- When showing multiple steps of the same equation, each on its own line:
  <p><span class="math">\\[ step1 \\]</span></p>
  <p><span class="math">\\[ step2 \\]</span></p>
- Do NOT use markdown formatting
- Do NOT use ```html or any code fences
- Do NOT use bullet points for math steps
- Always close tags properly

Example of correct format:
<p class="answers-ms"><strong>a)</strong> The points given are \\( P(0, 2) \\) and \\( Q(3, 8) \\).</p>

<p>The formula for the gradient \\( m \\) between two points is:</p>

<p><span class="math">\\[ m = \\frac{{y_2 - y_1}}{{x_2 - x_1}} \\]</span></p>
<p><span class="math">\\[ m = \\frac{{8 - 2}}{{3 - 0}} = \\frac{{6}}{{3}} = 2 \\]</span></p>
<p>So, the gradient is \\( 2 \\).</p>

<p class="answers-ms"><strong>b)</strong> Using the point-slope form:</p>
<p><span class="math">\\[ y - y_1 = m(x - x_1) \\]</span></p>
<p>Substituting m = 2 and point P(0, 2):</p>
<p><span class="math">\\[ y - 2 = 2(x - 0) \\]</span></p>
<p><span class="math">\\[ y = 2x + 2 \\]</span></p>
<p>So, the equation is y = 2x + 2.</p>
"""

EXPLANATION_USER_PROMPT = """Generate a detailed, step-by-step explanation for the following question:

QUESTION:
{question}

SUBJECT: {subject}
TOPIC: {topic}

Provide a complete solution that:
1. Identifies what the question is asking for each part (a, b, c, etc.)
2. Shows all working with clear mathematical steps
3. Explains the reasoning behind each step
4. Uses formulas and key concepts where appropriate
5. Arrives at a clear final answer for each part

IMPORTANT FORMATTING REQUIREMENTS:
- Start each answer part with: <p class="answers-ms"><strong>a)</strong> [explanation]</p>
- Use <p><span class="math">\\[ equation \\]</span></p> for display math
- Use \\( equation \\) for inline math within paragraphs
- Show step-by-step working with separate equation lines
- Write in clear, educational language that explains WHY steps are taken
- Follow IB marking scheme style

Output ONLY the HTML-formatted explanation. Do not include any preamble, markdown, or code fences."""


def generate_explanation(
    question: str,
    subject: str = "",
    topic: str = ""
) -> dict:
    """
    Generate a detailed explanation/answer for a given question using AI.
    
    Args:
        question: The HTML content of the question
        subject: Subject name (e.g., "Math AA HL")
        topic: Topic name (e.g., "Calculus")
        
    Returns:
        dict with 'success', 'explanation', and optional 'error'
    """
    try:
        # Initialize if needed
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
        )
        
        # Clean HTML for better processing
        import re
        clean_question = re.sub(r'<[^>]+>', ' ', question)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", EXPLANATION_SYSTEM_PROMPT),
            ("human", EXPLANATION_USER_PROMPT),
        ])
        
        # Generate explanation
        chain = prompt | llm
        response = chain.invoke({
            "question": clean_question[:2000],
            "subject": subject,
            "topic": topic,
        })
        
        return {
            "success": True,
            "explanation": response.content,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
