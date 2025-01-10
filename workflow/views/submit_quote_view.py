from django.http import JsonResponse, FileResponse

from django.core.mail import send_mail

from django.contrib import messages
from django.contrib.staticfiles.finders import find

from django.shortcuts import get_object_or_404

from io import BytesIO

from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from workflow.models import Job
from workflow.utils import extract_messages

import logging

logger = logging.getLogger(__name__)


def collect_pricing_data(pricing):
    """
    Collects time, material, and adjustment entries from a JobPricing instance.

    Args:
        job_pricing (JobPricing): The JobPricing instance.

    Returns:
        dict: A dictionary containing structured data for time, material, and adjustment entries.
    """
    time_entries = [
        ["Description", "Items", "Mins/Item", "Total Minutes", "Wage Rate", "Charge Rate"]
    ]
    material_entries = [
        ["Item Code", "Description", "Quantity", "Cost Rate", "Retail Rate", "Revenue"]
    ]
    adjustment_entries = [
        ["Description", "Cost Adj.", "Revenue", "Comments"]
    ]

    # Collect time entries
    for entry in pricing.time_entries.all():
        time_entries.append([
            entry.description or "N/A",
            entry.items or 0,
            f"{entry.minutes_per_item:.2f}" if entry.minutes_per_item else "0.00",
            f"{entry.minutes:.2f}",
            f"NZD {entry.wage_rate:.2f}",
            f"NZD {entry.charge_out_rate:.2f}"
        ])

    # Collect material entries
    for entry in pricing.material_entries.all():
        material_entries.append([
            entry.item_code or "N/A",
            entry.description or "N/A",
            f"{entry.quantity:.2f}" if entry.quantity else "0.00",
            f"NZD {entry.unit_cost:.2f}",
            f"NZD {entry.unit_revenue:.2f}",
            f"NZD {entry.revenue:.2f}"
        ])

    # Collect adjustment entries
    for entry in pricing.adjustment_entries.all():
        adjustment_entries.append([
            entry.description or "N/A",
            f"NZD {entry.cost_adjustment:.2f}",
            f"NZD {entry.price_adjustment:.2f}",
            entry.comments or "N/A"
        ])

    return {
        "time_entries": time_entries,
        "material_entries": material_entries,
        "adjustment_entries": adjustment_entries
    }


def create_pdf(job):
    """
    Generate a PDF for the given job, including a quotes table.

    Args:
        job: The Job instance for which the PDF will be generated.

    Returns:
        BytesIO: A buffer containing the generated PDF.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    logo_path = find("logo_msm.png")

    try:
        pdf.drawImage(
            logo_path,
            x=450, # Position near the right margin
            y=720, # Position near the top margin
            width=100, # Width matching jsPDF logo
            height=50, # Height matching jsPDF logo            
            preserveAspectRatio=True, # Maintain aspect ratio
            anchor='ne' # Anchor to the top-right corner
        )
    except Exception as e:
        logger.debug(f"Error loading logo: {e}")

    # Header with job and client information
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 750, f"Quote Summary for {job.name}")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 720, f"Client: {job.client.name if job.client else 'N/A'}")
    pdf.drawString(
        50,
        700,
        f"Contact: {job.client.email if job.client.email else job.contact_person or 'N/A'}",
    )
    pdf.drawString(50, 690, f"Job Number: {job.job_number if job.job_number else 'N/A'}")
    pdf.drawString(50, 680, f"Job Description: {job.description[:200] if job.description else 'N/A'}...")

    # Add a margin between job information and the first table
    start_y = 600  

    total_width = 500 
    table_styles = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#000080")),  
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),  
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),  
        ("ALIGN", (0, 1), (0, -1), "LEFT"),  
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ])

    # Render each section with adjusted column widths and spacing
    for idx, (section, data) in enumerate(collect_pricing_data(job.latest_quote_pricing).items()):
        pdf.setFont("Helvetica-Bold", 14)

        pdf.drawString(50, start_y, section.replace("_", " ").title())

        # Add space between the title and the table
        if idx == 0:
            start_y -= 75
        else:
            start_y -= 30

        # Calculate column widths proportional to the total width
        num_columns = len(data[0])
        column_width = total_width / num_columns
        col_widths = [column_width] * num_columns

        # Create and style the table
        table = Table(data, colWidths=col_widths)
        table.setStyle(table_styles)
        table.wrapOn(pdf, 50, start_y - 20)
        table.drawOn(pdf, 50, start_y - 20)

        # Adjust for table height and spacing
        start_y -= (len(data) * 15 + 20)

    # Footer
    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(50, 50, "Generated by Morris Sheetmetals - Workflow App")
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer


def generate_quote_pdf(request, job_id):
    """
    Generate a PDF quote summary for a specific job.

    Args:
        request: The HTTP request object
        job_id: The ID of the job to generate the PDF for

    Returns:
        FileResponse: A PDF file response containing the quote summary

    Raises:
        Http404: If the job with the given ID does not exist
    """
    job = get_object_or_404(Job, pk=job_id)
    pdf_buffer = create_pdf(job)

    return FileResponse(
        pdf_buffer,
        as_attachment=False,
        filename=f"quote_summary_{job.name}.pdf",
        content_type="application/pdf",
    )

# Not working yet: CSRF Token missing + Lacking a valid e-mail
def send_quote_email(request, job_id):
    """
    Send a quote summary for a specific job via email.

    Args:
        request: The HTTP request object
        job_id: The ID of the job to send the quote for

    Returns:
        HttpResponse: A success message indicating the email was sent

    Raises:
        Http404: If the job with the given ID does not exist
    """
    job = get_object_or_404(Job, pk=job_id)
    email = job.client.email if job.client and job.client.email else None

    if not email:
        messages.error(request, "Client email not found")
        return JsonResponse(
            {"error": "Client email not found", "messages": extract_messages(request)},
            status=400,
        )

    pdf_buffer = create_pdf(job)
    pdf_content = pdf_buffer.getvalue()
    pdf_buffer.close()

    send_mail(
        subject=f"Quote Summary for {job.name}",
        message=f"Please find the attached quote summary for {job.name}.",
        from_email="",  # Need to configure a real domain to send e-mails
        recipient_list=[email],
        fail_silently=False,
        html_message=f"<p>Please find the attached quote summary for {job.name}.</p>",
        attachments=[
            (f"quote_summary_{job.name}.pdf", pdf_content, "application/pdf")
        ],
    )

    messages.success(request, "Email sent successfully")
    return JsonResponse({"success": True, "messages": extract_messages(request)})
