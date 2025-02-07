import logging
import os
from io import BytesIO

from django.conf import settings
from PIL import Image
from PyPDF2 import PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# A4 dimensions (210 x 297 mm)
PAGE_WIDTH, PAGE_HEIGHT = A4  # 595 x 842 points
MARGIN = 50  # points
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)  # 495 points


def get_image_dimensions(image_path):
    """Get image dimensions and scale if wider than content width."""
    with Image.open(image_path) as img:
        img_width, img_height = img.size
        # Convert pixels to points (72 points per inch, assuming 72 DPI images)
        img_width_pt = img_width
        img_height_pt = img_height

        # Only scale down if image is wider than content area
        if img_width_pt > CONTENT_WIDTH:
            scale = CONTENT_WIDTH / img_width_pt
            img_width_pt = CONTENT_WIDTH
            img_height_pt = img_height_pt * scale

        return img_width_pt, img_height_pt


def create_workshop_pdf(job):
    """
    Generate a workshop PDF for the given job, including job details and marked files.

    Args:
        job: The Job instance for which the PDF will be generated.

    Returns:
        BytesIO: A buffer containing the generated PDF.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    try:
        # Add logo if available
        logo_path = os.path.join(settings.BASE_DIR, "workflow/static/logo_msm.png")
        if os.path.exists(logo_path):
            pdf.drawImage(
                logo_path,
                MARGIN,
                PAGE_HEIGHT - 100,
                width=100,
                height=50,
                preserveAspectRatio=True,
            )

        # Job Details
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(MARGIN, PAGE_HEIGHT - 150, f"Workshop Sheet - {job.name}")

        pdf.setFont("Helvetica", 12)
        details = [
            ("Job Number:", job.job_number),
            ("Client:", job.client.name if job.client else "N/A"),
            ("Contact:", job.contact_person or "N/A"),
            ("Description:", job.description or "N/A"),
        ]

        y = PAGE_HEIGHT - 200
        for label, value in details:
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(MARGIN, y, label)
            pdf.setFont("Helvetica", 12)
            pdf.drawString(MARGIN + 100, y, str(value))
            y -= 20

        # Add marked files
        files_to_print = job.files.filter(print_on_jobsheet=True)
        if files_to_print.exists():
            pdf.showPage()  # Start a new page for files
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(MARGIN, PAGE_HEIGHT - MARGIN, "Attached Files")

            y = PAGE_HEIGHT - 100
            for job_file in files_to_print:
                # Add file name
                pdf.setFont("Helvetica", 12)
                pdf.drawString(MARGIN, y, job_file.filename)
                y -= 20

                # Get full path to file
                file_path = os.path.join(
                    settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path
                )
                if not os.path.exists(file_path):
                    continue

                # Handle different file types
                if job_file.mime_type.startswith("image/"):
                    try:
                        # Get natural dimensions, scaling down if too wide
                        width, height = get_image_dimensions(file_path)

                        # Center the image
                        x = MARGIN + (CONTENT_WIDTH - width) / 2

                        # Check if we need a new page
                        if y - height < MARGIN:
                            pdf.showPage()
                            y = PAGE_HEIGHT - MARGIN

                        # Draw at natural size (or scaled if was too wide)
                        pdf.drawImage(
                            file_path, x, y - height, width=width, height=height
                        )
                        y -= height + 20  # 20pt padding after image
                    except Exception as e:
                        logger.error(f"Failed to add image {job_file.filename}: {e}")
                        pdf.setFont("Helvetica", 10)
                        pdf.drawString(MARGIN + 20, y, f"Error adding image: {str(e)}")
                        y -= 20

                elif job_file.mime_type == "application/pdf":
                    try:
                        # Note that we'll merge PDFs after generating the main document
                        pdf.setFont("Helvetica", 10)
                        pdf.drawString(MARGIN + 20, y, "PDF will be appended")
                        y -= 20
                    except Exception as e:
                        logger.error(f"Failed to note PDF {job_file.filename}: {e}")
                        pdf.setFont("Helvetica", 10)
                        pdf.drawString(MARGIN + 20, y, f"Error with PDF: {str(e)}")
                        y -= 20
                else:
                    # For unsupported files, just note their presence
                    pdf.setFont("Helvetica", 10)
                    pdf.drawString(
                        MARGIN + 20,
                        y,
                        f"File type not supported for preview: {job_file.mime_type}",
                    )
                    y -= 20

                if y < 50:  # Start a new page if needed
                    pdf.showPage()
                    y = 750

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
