import logging.handlers
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from io import BytesIO
from gpt_tools import *
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from queue import Queue
from logging.handlers import QueueHandler, QueueListener
from datetime import datetime

EXAMPLES_PATH = os.path.join('data', 'examples')

# Logging
log_queue = Queue()
queue_handler = QueueHandler(log_queue)
queue_listener = QueueListener(log_queue, logging.FileHandler('app-logging.txt'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(queue_handler)


@catch_error(logger)
def get_eval(client:Any, 
                   input_file_path, 
                   model='gpt-4o-mini', 
                   hyperparameters:dict=None, 
                   examples_path:str=None):
    return get_evaluation(client, input_file_path, model, hyperparameters, examples_path)


def allowed_file(file):
    """
    Checks if the uploaded file has an allowed extension (PDF or DOCX).
    
    Args:
        file (werkzeug.datastructures.FileStorage): Uploaded file.
    
    Returns:
        bool: True if file extension is allowed, False otherwise.
    """
    return os.path.splitext(file.filename)[-1].lower() in ('.pdf', '.docx')


def generate_pdf(eval:str,
                 x_margin:int=40,
                 y_margin:int=750,
                 line_height:int=15,
                 section_space:int=20, 
                 header_font_size=15, 
                 body_font_size=12):
    """
    Generates a PDF file from the evaluation string.

    Args:
        eval (str): The evaluation text returned by get_eval() function.
        x_margin (int, optional): Left margin for text placement. Defaults to 40.
        y_margin (int, optional): Top margin for text placement. Defaults to 750.
        line_height (int, optional): Line height for text spacing. Defaults to 15.
        section_space (int, optional): Space between sections. Defaults to 20.
        header_font_size (int, optional): Font size for header text. Defaults to 15.
        body_font_size (int, optional): Font size for body text. Defaults to 12.

    Returns:
        BytesIO: A PDF file stream ready for download.
    """
    output = BytesIO()

    pdf_canvas = canvas.Canvas(output, pagesize=letter)

    def draw_header_footer(pdf_canvas, page_number):
        """
        Draws a header and footer on each PDF page.
        
        Args:
            pdf_canvas (canvas.Canvas): The canvas to draw on.
            page_number (int): Current page number.
        """

        # Header
        pdf_canvas.setFont('Helvetica-Bold', header_font_size)
        pdf_canvas.setFillColor(colors.black)
        pdf_canvas.drawString(x_margin, y_margin, 'TOK Evaluation Report')
        
        # Footer
        pdf_canvas.setFont('Helvetica', 10)
        pdf_canvas.setFillColor(colors.black)
        pdf_canvas.drawString(x_margin, 30, f"Page {page_number}")

    lines = eval.split('\n')
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
        pdf_canvas.setFont('Helvetica', body_font_size)
        pdf_canvas.setFillColor(colors.grey)
        pdf_canvas.drawString(x_margin, y_margin, line.strip())
        y_margin -= line_height

    pdf_canvas.save()

    output.seek(0)

    return output


load_dotenv(find_dotenv())
client = OpenAI()


app = Flask(__name__)


@app.route('/')
def index():
    """
    Renders the main index page.
    
    Returns:
        str: Rendered HTML template for the index page.
    """
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handles file upload, evaluates the file content, and returns a generated PDF.

    Logs errors for missing, invalid, or unsupported file formats. If the file is valid,
    it evaluates the content using a GPT model and returns a downloadable PDF with the results.

    Returns:
        Response: PDF file or error response depending on outcome.
    """
    if 'file' not in request.files:
        logger.warning(f'{datetime.now()}\tNo file part in request.')
        return 'No file part', 400
    
    file = request.files['file']
    if file.filename == '':
        logger.warning(f'{datetime.now()}\tNo selected file')
        return 'No selected file', 400
    
    if file and allowed_file(file):
        logger.info(f'{datetime.now()}\tProcessing file: {file.filename}')
        try:
            eval = get_eval(client,
                            file,
                            hyperparameters={'temperature':0.2, 'top_p':.3}, 
                            examples_path=EXAMPLES_PATH)
            eval_pdf_stream = generate_pdf(eval)
            return send_file(eval_pdf_stream, as_attachment=True, download_name='TOK-evaluation.pdf')
        except Exception as e:
            logger.error(f"{datetime.now()}\tError processing file {file.filename}: {str(e)}", exc_info=True)
            return 'File processing error', 500
    logger.warning(f'{datetime.now()}\tInvalid file format: {file.filename}')
    return 'Invalid file format', 400

if __name__ == '__main__':
    """
    Starts the Flask application and the logging queue listener.
    
    Ensures graceful shutdown of the logging listener when the app stops.
    """
    try:
        queue_listener.start()
        app.run(debug=True)
    finally:
        logger.info(f'{datetime.now()}\tApp shutting down.')
        queue_listener.stop()
