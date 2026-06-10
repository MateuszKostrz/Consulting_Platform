import logging
import os
from io import BytesIO
from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings
from .tools import get_evaluation
import openai
from decouple import config
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import threading
import textwrap

# Initialize OpenAI client
api_key = config('OPENAI_API_KEY')
client = openai.OpenAI(api_key=api_key)

# Define the examples path globally
EXAMPLES_PATH = os.path.join(settings.BASE_DIR, 'website', 'data')
examples_json_path = os.path.join(settings.BASE_DIR, 'website', 'data')

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# PDF Generation Function
def generate_pdf(eval: str,
                 logo_path: str,
                 x_margin: int = 40,
                 y_margin: int = 700,
                 line_height: int = 20,
                 section_space: int = 30,
                 body_font_size: int = 12):
    """
    Generates a PDF file from the evaluation string.

    Args:
        eval (str): The evaluation text returned by the `get_eval()` function.
        logo_path (str): Path to the company logo PNG file.
        x_margin (int, optional): Left margin for text placement. Defaults to 40.
        y_margin (int, optional): Top margin for text placement. Defaults to 700.
        line_height (int, optional): Line height for text spacing. Defaults to 20.
        section_space (int, optional): Space between sections. Defaults to 30.
        header_font_size (int, optional): Font size for header text. Defaults to 20.
        body_font_size (int, optional): Font size for body text. Defaults to 12.

    Returns:
        BytesIO: A PDF file stream ready for download.
    """

    output = BytesIO()
    pdf_canvas = canvas.Canvas(output, pagesize=letter)
    pdf_canvas.setFillColor(colors.black)

    def draw_header(pdf_canvas):
        """Draws the logo and the 'TOK Evaluation Report' header."""
        # Draw the logo
        logo = ImageReader(logo_path)
        pdf_canvas.drawImage(logo, 180, 650, width=250, height=120, mask='auto')

    def draw_footer(pdf_canvas, page_number):
        """Draws a footer with the page number."""
        pdf_canvas.setFont('Helvetica', 10)
        pdf_canvas.drawString(x_margin, 30, f"Page {page_number}")

    page_number = 1

    # Draw the header for the first page
    draw_header(pdf_canvas)
    y_margin -= 100
    pdf_canvas.setFont('Helvetica-Bold', 16)
    pdf_canvas.drawString(x_margin, y_margin, 'Report')
    y_margin -= section_space
    draw_footer(pdf_canvas, page_number)

    lines = eval.split('\n')

    for line in lines:
        for subline in textwrap.wrap(line.strip(), width=90):
            if y_margin < 50:  # Create a new page when space runs out
                pdf_canvas.showPage()
                page_number += 1
                draw_header(pdf_canvas)
                draw_footer(pdf_canvas, page_number)
                y_margin = 700 - section_space

            if subline.strip().startswith(('Grade', 'Score')):
                pdf_canvas.setFont('Helvetica-Bold', body_font_size)
                pdf_canvas.drawString(x_margin, y_margin, subline)
                y_margin -= line_height
            elif subline.strip()[0].isdigit():
                y_margin -= line_height
                pdf_canvas.setFont('Helvetica', body_font_size)
                pdf_canvas.drawString(x_margin, y_margin, subline)
                y_margin -= line_height
            else:
                pdf_canvas.setFont('Helvetica', body_font_size)
                pdf_canvas.drawString(x_margin, y_margin, subline)
                y_margin -= line_height


    pdf_canvas.save()
    output.seek(0)
    return output

def process_uploaded_ps(file, examples_dir: str = EXAMPLES_PATH):
    try:
        # Step 1: Get the evaluation from the GPT model with examples
        examples_json_path = os.path.join(settings.BASE_DIR, 'website', 'data')  # Define the path to your examples

        # If examples_dir is not provided, use the default
        examples_as_json = examples_dir or examples_json_path


        evaluation = get_evaluation(client, file, examples_as_json=examples_as_json)  # Pass 'examples_as_json'

        # Step 2: Generate a PDF report from the evaluation
        pdf_stream = generate_pdf(evaluation, 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTDj5twt6re_-AM0u_EKV5CvYqu2-J5BJA9Dmbu17khHTIVM2Zt-C_UXJ-95HZtCluDETA&usqp=CAU')

        return pdf_stream

    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        raise e