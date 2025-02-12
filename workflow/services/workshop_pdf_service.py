import logging
import os
from io import BytesIO

from django.conf import settings
from PIL import Image
from PyPDF2 import PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

# A4 page dimensions (210 x 297 mm)
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 50
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

styles = getSampleStyleSheet()
description_style = styles["Normal"]


def get_image_dimensions(image_path):
    """Gets the image dimensions and scales it if larger than content width."""
    with Image.open(image_path) as img:
        img_width, img_height = img.size
        # Considering 1 pixel = 1 point
        img_width_pt, img_height_pt = img_width, img_height

        if img_width_pt > CONTENT_WIDTH:
            scale = CONTENT_WIDTH / img_width_pt
            img_width_pt = CONTENT_WIDTH
            img_height_pt *= scale

        return img_width_pt, img_height_pt


def create_workshop_pdf(job):
    """
    Generates a PDF for the given job, including details and marked files.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    try:
        # Define initial position
        y_position = PAGE_HEIGHT - MARGIN

        # Add logo (with transparency if applicable)
        logo_path = os.path.join(settings.BASE_DIR, "workflow/static/logo_msm.png")
        if os.path.exists(logo_path):
            logo = ImageReader(logo_path)
            # Calculate x position to center the image
            x = MARGIN + (CONTENT_WIDTH - 150) / 2  # 150 is the image width
            pdf.drawImage(logo, x, y_position - 150, width=150, height=150, mask='auto')            
            y_position -= 200 # Space to avoid overlap

        # Add main title
        pdf.setFillColor(colors.HexColor("#004aad"))
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(MARGIN, y_position, f"Workshop Sheet - {job.name}")
        pdf.setFillColor(colors.black)
        y_position -= 30

        # Build a table with Job details, including description with wrap
        job_details = [
            ["Job Number", job.job_number or "N/A"],
            ["Client", job.client.name if job.client else "N/A"],
            ["Contact", job.contact_person or "N/A"],
            # Using Paragraph for description ensures text will wrap automatically
            ["Description", Paragraph(job.description or "N/A", description_style)]
        ]

        details_table = Table(job_details, colWidths=[150, CONTENT_WIDTH - 150])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#004aad")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        table_width, table_height = details_table.wrap(CONTENT_WIDTH, PAGE_HEIGHT)
        details_table.drawOn(pdf, MARGIN, y_position - table_height)
        y_position -= table_height + 20

        # Attach Files Marked for Printing
        files_to_print = job.files.filter(print_on_jobsheet=True)
        if files_to_print.exists():
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(MARGIN, PAGE_HEIGHT - MARGIN, "Attached Files")
            y_position = PAGE_HEIGHT - 100

            for job_file in files_to_print:
                pdf.setFont("Helvetica", 12)
                pdf.drawString(MARGIN, y_position, job_file.filename)
                y_position -= 20

                file_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path)
                if not os.path.exists(file_path):
                    continue

                if job_file.mime_type.startswith("image/"):
                    try:
                        width, height = get_image_dimensions(file_path)
                        x = MARGIN + (CONTENT_WIDTH - width) / 2

                        # If image won't fit on page, create a new page
                        if y_position - height < MARGIN:
                            pdf.showPage()
                            y_position = PAGE_HEIGHT - MARGIN

                        # Add image with mask='auto' parameter to handle transparency
                        pdf.drawImage(file_path, x, y_position - height, width=width, height=height, mask='auto')
                        y_position -= height + 20
                    except Exception as e:
                        logger.error(f"Failed to add image {job_file.filename}: {e}")
                        pdf.drawString(MARGIN + 20, y_position, f"Error adding image: {str(e)}")
                        y_position -= 20

                elif job_file.mime_type == "application/pdf":
                    pdf.drawString(MARGIN + 20, y_position, "PDF will be appended")
                    y_position -= 20

                if y_position < 50:
                    pdf.showPage()
                    y_position = PAGE_HEIGHT - 100

        pdf.save()
        buffer.seek(0)

        # If there are attached PDFs, merge them
        pdf_files = [f for f in files_to_print if f.mime_type == "application/pdf"]
        if not pdf_files:
            return buffer

        merger = PdfWriter()
        merger.append(buffer)

        for job_file in pdf_files:
            file_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path)
            if os.path.exists(file_path):
                try:
                    merger.append(file_path)
                except Exception as e:
                    logger.error(f"Failed to merge PDF {job_file.filename}: {e}")

        merged_buffer = BytesIO()
        merger.write(merged_buffer)
        merged_buffer.seek(0)

        buffer.close()
        return merged_buffer

    except Exception as e:
        buffer.close()
        raise e
