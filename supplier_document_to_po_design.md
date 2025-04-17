# Supplier Document to Purchase Order Design

## Overview

This document outlines the architecture for the supplier document to purchase order (PO) functionality. This feature allows users to upload supplier documents (invoices, price lists, etc.), extract structured data using Claude AI, and use that data to pre-fill a purchase order form.

## Data Model

### Core Entities

```
PurchaseOrder
  |
  +-- PurchaseOrderSupplierQuote (one-to-one relationship)
```

The `PurchaseOrderSupplierQuote` model stores:
- Original document metadata (filename, file_path, mime_type)
- Extracted structured data from the document (extracted_data JSONField)
- Processing status information

This design maintains a clear one-to-one relationship between a purchase order and its supplier quote, reflecting the business reality that a purchase order is exclusively created based on a single supplier quote.

## Process Flow

1. **Document Upload**
   - User uploads a supplier document (PDF, image, etc.)
   - Document is temporarily stored
   - System extracts data using Claude AI

2. **PO Creation and Pre-filling**
   - System creates a new PurchaseOrder with draft status
   - System creates a PurchaseOrderSupplierQuote to store the uploaded document and extracted data
   - System pre-fills the PurchaseOrder with data from the supplier quote:
     - Supplier information 
     - Line items with descriptions, quantities, and prices
     - Some information may not be available, due to extraction errors
   - Document file is moved to permanent storage


3. **PO Form Loading**
   - User is redirected to the PO edit form
   - PO form loads with the pre-filled data
   - User can see the extracted and pre-filled information

4. **PO Completion**
   - User reviews and completes the PO
   - User can modify any pre-filled data as needed
   - User submits the PO to Xero when ready

## Component Architecture

### Document Processing Service

The document processing service will:
- Handle temporary file storage
- Coordinate data extraction with Claude AI
- Create the PurchaseOrder and associated PurchaseOrderSupplierQuote
- Pre-fill the PurchaseOrder with extracted data
- Move the document to permanent storage
- Handle error cases and cleanup

### PO Form View

The PO form view will:
- Load the PurchaseOrder with its associated supplier quote data
- Display the pre-filled data to the user
- Handle form submission and updates

### Form Rendering

The Django view will:
- Load the PurchaseOrder with its associated supplier quote data
- Render the form with the pre-filled data
- Allow user overrides of any pre-filled data

## State Management

### Valid States

1. **PO without Supplier Document**
   - Standard PO with no associated supplier document
   - All fields must be manually filled

2. **PO with Supplier Document**
   - PO with associated PurchaseOrderSupplierQuote
   - Form fields pre-filled from extracted document data
   - Document metadata stored for reference

### Error Handling

The system will handle:
- Document upload failures
- Data extraction failures
- PO creation failures
- Form validation errors

Each error case will have appropriate user feedback and logging.

## Benefits of This Architecture

1. **Clear Separation of Concerns**
   - PurchaseOrder model focuses on order details
   - PurchaseOrderSupplierQuote model handles document data
   - Clearer code paths and responsibilities

2. **Data Integrity**
   - One-to-one relationship ensures data consistency
   - Document data is always tied to its PO
   - No risk of orphaned or mismatched records

3. **Flexibility**
   - PurchaseOrder model remains clean and focused
   - Document processing logic is isolated
   - Easier to extend or modify document handling

4. **Maintainability**
   - Clear model boundaries
   - Logical separation of concerns
   - Easier to understand and modify