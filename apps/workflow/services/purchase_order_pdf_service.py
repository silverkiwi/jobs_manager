import logging
import os
from io import BytesIO
from datetime import datetime

from django.conf import settings
from PIL import Image, ImageFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from apps.workflow.models.purchase import PurchaseOrder

logger = logging.getLogger(__name__)

# A4 page dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 50
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# Initialize styles
styles = getSampleStyleSheet()
normal_style = styles["Normal"]
bold_style = styles["Heading4"]
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Primary color for headers
PRIMARY_COLOR = colors.HexColor("#000080")  # Navy blue

class PurchaseOrderPDFGenerator:
    """
    Generator class for Purchase Order PDF documents.
    """
    
    def __init__(self, purchase_order):
        """
        Initialize the PDF generator with a purchase order.
        
        Args:
            purchase_order: The PurchaseOrder model instance to generate PDF for
        """
        self.purchase_order = purchase_order
        self.buffer = BytesIO()
        self.pdf = canvas.Canvas(self.buffer, pagesize=A4)
        self.y_position = PAGE_HEIGHT - MARGIN
    
    def generate(self):
        """
        Generate the complete PDF document.
        Returns:
            BytesIO: Buffer containing the generated PDF
        """
        try:
            # Add content to PDF
            self.y_position = self.add_logo(self.y_position)
            self.y_position = self.add_header_info(self.y_position)
            self.y_position = self.add_supplier_info(self.y_position)
            self.y_position = self.add_line_items_table(self.y_position)
            
            # Save PDF and return buffer
            self.pdf.save()
            self.buffer.seek(0)
            return self.buffer
            
        except Exception as e:
            logger.exception(f"Error generating PDF for PO {self.purchase_order.id}: {str(e)}")
            raise
    
    def add_logo(self, y_position):
        """Add company logo to the PDF."""
        logo_path = os.path.join(settings.BASE_DIR, "workflow/static/logo_msm.png")
        if not os.path.exists(logo_path):
            logger.warning(f"Logo file not found at {logo_path}")
            return y_position
            
        try:
            logo = ImageReader(logo_path)
            # Position logo in top right corner
            self.pdf.drawImage(
                logo, 
                PAGE_WIDTH - MARGIN - 120,  # X position (right aligned)
                y_position - 80,            # Y position
                width=120, 
                height=80, 
                mask="auto",
                preserveAspectRatio=True
            )
            return y_position - 20  # Return updated position with less space used
        except Exception as e:
            logger.warning(f"Failed to add logo: {str(e)}")
            return y_position
    
    def add_header_info(self, y_position):
        """Add purchase order header and details to the PDF."""
        # Draw title
        self.pdf.setFont("Helvetica-Bold", 18)
        self.pdf.setFillColor(PRIMARY_COLOR)
        self.pdf.drawString(MARGIN, y_position, f"Purchase Order: {self.purchase_order.po_number}")
        self.pdf.setFillColor(colors.black)
        y_position -= 30
        
        # Draw PO details
        details_data = [
            ["Order Date:", self.purchase_order.order_date.strftime("%d %b %Y")],
            ["Expected Delivery:", self.purchase_order.expected_delivery.strftime("%d %b %Y") if self.purchase_order.expected_delivery else "Not specified"],
            ["Status:", self.purchase_order.status.title()],
            ["Reference:", self.purchase_order.reference or "N/A"],
        ]
        
        details_table = Table(details_data, colWidths=[120, 180])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        table_width, table_height = details_table.wrap(CONTENT_WIDTH, PAGE_HEIGHT)
        details_table.drawOn(self.pdf, MARGIN, y_position - table_height)
        
        return y_position - table_height - 20
    
    def add_supplier_info(self, y_position):
        """Add supplier information section to the PDF."""
        # Add section title
        self.pdf.setFont("Helvetica-Bold", 12)
        self.pdf.drawString(MARGIN, y_position, "Supplier Information")
        y_position -= 20
        
        # Create supplier info table
        supplier = self.purchase_order.supplier
        if supplier:
            supplier_data = [
                ["Name:", supplier.name],
                ["Email:", supplier.email or "N/A"],
                ["Phone:", supplier.phone or "N/A"],
                ["Address:", supplier.address or "N/A"],
            ]
        else:
            supplier_data = [["Supplier:", "Not specified"]]
        
        supplier_table = Table(supplier_data, colWidths=[80, 300])
        supplier_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        table_width, table_height = supplier_table.wrap(CONTENT_WIDTH, PAGE_HEIGHT)
        supplier_table.drawOn(self.pdf, MARGIN, y_position - table_height)
        
        # Draw horizontal line
        y_position = y_position - table_height - 15
        self.pdf.setStrokeColor(colors.lightgrey)
        self.pdf.line(MARGIN, y_position, PAGE_WIDTH - MARGIN, y_position)
        
        return y_position - 20
    
    def add_line_items_table(self, y_position):
        """Add the table of purchase order line items."""
        # Section title
        self.pdf.setFont("Helvetica-Bold", 14)
        self.pdf.drawString(MARGIN, y_position, "Order Items")
        y_position -= 25
        
        # Create table header
        header = ["Description", "Quantity", "Unit Cost", "Total"]
        
        # Get PO lines data
        lines_data = [header]
        total_cost = 0
        
        # Add each PO line as a row
        for line in self.purchase_order.po_lines.all():
            unit_cost = line.unit_cost if line.unit_cost is not None else "TBC"
            
            if line.unit_cost is not None:
                line_total = line.quantity * line.unit_cost
                total_cost += line_total
                total_display = f"${line_total:.2f}"
            else:
                total_display = "TBC"
            
            # Add row to table data
            lines_data.append([
                line.description,
                str(line.quantity),
                f"${unit_cost:.2f}" if isinstance(unit_cost, (float, int, complex)) else unit_cost,
                total_display
            ])
        
        # Add total row
        lines_data.append(["", "", "Total:", f"${total_cost:.2f}"])
        
        # Define column widths
        col_widths = [
            CONTENT_WIDTH * 0.5,  # Description (50%)
            CONTENT_WIDTH * 0.15, # Quantity (15%)
            CONTENT_WIDTH * 0.15, # Unit cost (15%)
            CONTENT_WIDTH * 0.2   # Total (20%)
        ]
        
        # Create the table
        lines_table = Table(lines_data, colWidths=col_widths)
        
        # Style the table
        table_style = TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            # Content rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            # Borders
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])
        lines_table.setStyle(table_style)
        
        # Check if table fits on current page
        table_width, table_height = lines_table.wrap(CONTENT_WIDTH, PAGE_HEIGHT)
        if y_position - table_height < MARGIN + 50:  # 50 is space for footer
            self.pdf.showPage()
            y_position = PAGE_HEIGHT - MARGIN
            # Redraw title on new page
            self.pdf.setFont("Helvetica-Bold", 14)
            self.pdf.drawString(MARGIN, y_position, "Order Items (Continued)")
            y_position -= 25
        
        lines_table.drawOn(self.pdf, MARGIN, y_position - table_height)
        return y_position - table_height - 20


def create_purchase_order_pdf(purchase_order):
    """
    Factory function to generate a PDF for a purchase order.
    
    Args:
        purchase_order: The PurchaseOrder instance
        
    Returns:
        BytesIO: Buffer containing the generated PDF
    """
    generator = PurchaseOrderPDFGenerator(purchase_order)
    return generator.generate()
