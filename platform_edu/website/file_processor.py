import logging
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from .gpt_tools import get_evaluation
import openai
from decouple import config
from platform_edu import settings

# Initialize OpenAI client
api_key = config('OPENAI_API_KEY')
client = openai.OpenAI(api_key=api_key)

# Define the examples path globally
# EXAMPLES_PATH = os.path.join('data', 'examples')
EXAMPLES_PATH = os.path.join(settings.BASE_DIR, 'website', 'data', 'examples')


# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# PDF Generation Function
def generate_pdf(eval_str: str, x_margin=40, y_margin=750, line_height=15, section_space=20, header_font_size=15, body_font_size=12) -> BytesIO:
    output = BytesIO()
    pdf_canvas = canvas.Canvas(output, pagesize=letter)

    def draw_header_footer(pdf_canvas, page_number):
        # Header
        pdf_canvas.setFont('Helvetica-Bold', header_font_size)
        pdf_canvas.setFillColor(colors.black)
        pdf_canvas.drawString(x_margin, y_margin, 'Essay Evaluation Report')
        # Footer
        pdf_canvas.setFont('Helvetica', 10)
        pdf_canvas.setFillColor(colors.black)
        pdf_canvas.drawString(x_margin, 30, f"Page {page_number}")

    lines = eval_str.split('\n')
    page_number = 1
    draw_header_footer(pdf_canvas, page_number)
    y_margin -= section_space

    for line in lines:
        if y_margin < 40:
            pdf_canvas.showPage()
            page_number += 1
            y_margin = 750 - section_space
            draw_header_footer(pdf_canvas, page_number)
            y_margin -= section_space
        pdf_canvas.setFont('Helvetica', body_font_size)
        pdf_canvas.setFillColor(colors.grey)
        pdf_canvas.drawString(x_margin, y_margin, line.strip())
        y_margin -= line_height

    pdf_canvas.save()
    output.seek(0)
    return output

def process_uploaded_file(file, examples_dir: str = EXAMPLES_PATH):
    try:
        # Step 1: Get the evaluation from the GPT model with examples
        evaluation = get_evaluation(client, file, examples_dir=examples_dir)  # Updated to use 'examples_dir'

        # Step 2: Generate a PDF report from the evaluation
        pdf_stream = generate_pdf(evaluation)

        return pdf_stream

    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        raise e

