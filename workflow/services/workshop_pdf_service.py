import logging
import mimetypes
import os
from io import BytesIO
import time

from django.conf import settings
from PIL import Image, ImageFile
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

ImageFile.LOAD_TRUNCATED_IMAGES = True


def wait_until_file_ready(file_path, max_wait=10):
    """Tenta abrir o arquivo e fecha imediatamente. Se falhar, aguarda um pouco."""
    wait_time = 0
    while wait_time < max_wait:
        try:
            with open(file_path, "rb") as f:
                f.read(10)
            return
        except OSError:
            time.sleep(1)
            wait_time += 1


def get_image_dimensions(image_path):
    """Gets the image dimensions and scales it if larger than content width."""
    wait_until_file_ready(image_path)
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
            pdf.drawImage(logo, x, y_position - 150, width=150, height=150, mask="auto")
            y_position -= 200  # Space to avoid overlap

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
            ["Description", Paragraph(job.description or "N/A", description_style)],
        ]

        details_table = Table(job_details, colWidths=[150, CONTENT_WIDTH - 150])
        details_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004aad")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        table_width, table_height = details_table.wrap(CONTENT_WIDTH, PAGE_HEIGHT)
        details_table.drawOn(pdf, MARGIN, y_position - table_height)
        y_position -= table_height + 40

        # Add Materials Notes title
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(MARGIN, y_position, "Materials Notes")
        y_position -= 25

        # Add materials table
        materials_data = [["Description", "Quantity", "Comments"]]
        materials_data.extend([["", "", ""] for _ in range(5)])  # Add 5 empty rows

        materials_table = Table(
            materials_data,
            colWidths=[CONTENT_WIDTH * 0.4, CONTENT_WIDTH * 0.2, CONTENT_WIDTH * 0.4],
        )
        materials_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004aad")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )

        materials_width, materials_height = materials_table.wrap(
            CONTENT_WIDTH, PAGE_HEIGHT
        )
        materials_table.drawOn(pdf, MARGIN, y_position - materials_height)
        y_position -= materials_height + 20

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

                # Get full path to file
                file_path = os.path.join(
                    settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path
                )
                if not os.path.exists(file_path):
                    continue

                # Handle different file types
                if job_file.mime_type.startswith("image/"):
                    try:
                        width, height = get_image_dimensions(file_path)

                        # Center the image
                        x = MARGIN + (CONTENT_WIDTH - width) / 2

                        # If image won't fit on page, create a new page
                        if y_position - height < MARGIN:
                            pdf.showPage()
                            y_position = PAGE_HEIGHT - MARGIN

                        # Add image with mask='auto' parameter to handle transparency
                        pdf.drawImage(
                            file_path,
                            x,
                            y_position - height,
                            width=width,
                            height=height,
                        )
                        y_position -= height + 20
                    except Exception as e:
                        logger.error(f"Failed to add image {job_file.filename}: {e}")
                        error_text = Paragraph(
                            f"Error adding image: {str(e)}", description_style
                        )
                        error_text.wrapOn(pdf, CONTENT_WIDTH - 40, PAGE_HEIGHT)
                        error_text.drawOn(pdf, MARGIN + 20, y_position - 20)
                        y_position -= 40

                elif job_file.mime_type == "application/pdf":
                    pdf.drawString(MARGIN + 20, y_position, "PDF will be appended")
                    y_position -= 20

                if y_position < 50:
                    pdf.showPage()
                    y_position = PAGE_HEIGHT - 100

        # Save the main document
        pdf.save()
        buffer.seek(0)

        # If we have PDF attachments, merge them
        pdf_files = [f for f in files_to_print if f.mime_type == "application/pdf"]
        if not pdf_files:
            return buffer

        # Create a PDF merger with our main document
        merger = PdfWriter()
        merger.append(buffer)

        # Add each PDF attachment
        for job_file in pdf_files:
            file_path = os.path.join(
                settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path
            )
            if os.path.exists(file_path):
                try:
                    merger.append(file_path)
                except Exception as e:
                    logger.error(f"Failed to merge PDF {job_file.filename}: {e}")

        # Write the merged PDF to a new buffer
        merged_buffer = BytesIO()
        merger.write(merged_buffer)
        merged_buffer.seek(0)

        # Clean up and return
        buffer.close()
        return merged_buffer

    except Exception as e:
        buffer.close()
        raise e
