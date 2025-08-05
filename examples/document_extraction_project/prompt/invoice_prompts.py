"""Invoice extraction prompts for ZenML with enhanced features."""

from schemas.invoice_schema import InvoiceData, OCRInvoiceData

from zenml.prompts import Prompt

# Basic invoice extraction prompt
invoice_extraction_v1 = Prompt(
    template="""You are an expert invoice processing system. Extract structured data from this invoice text.

INVOICE TEXT:
{document_text}

CRITICAL REQUIREMENTS:
1. Return ONLY valid JSON matching the exact schema structure
2. Use null for missing values
3. Dates must be in YYYY-MM-DD format
4. Numbers should be numeric types, not strings
5. Line items must be an array of objects

Extract the data now:""",
    variables={"document_text": ""},
    output_schema=InvoiceData.model_json_schema(),
    examples=[
        {
            "input": {
                "document_text": "Invoice #INV-001\nDate: 2024-01-15\nFrom: ACME Corp\n1x Software License $100.00\nTotal: $100.00"
            },
            "output": {
                "invoice_number": "INV-001",
                "invoice_date": "2024-01-15",
                "due_date": None,
                "vendor": {
                    "name": "ACME Corp",
                    "address": None,
                    "phone": None,
                    "email": None,
                },
                "line_items": [
                    {
                        "description": "Software License",
                        "quantity": 1,
                        "unit_price": 100.0,
                        "total": 100.0,
                    }
                ],
                "subtotal": None,
                "tax_amount": None,
                "total_amount": 100.0,
                "currency": None,
                "po_number": None,
                "payment_terms": None,
                "notes": None,
            },
        }
    ],
)


# Enhanced invoice extraction prompt with comprehensive examples
invoice_extraction_v2 = Prompt(
    template="""You are an expert invoice processing AI. Extract structured data from invoices with high accuracy.

INVOICE TEXT:
{document_text}

EXTRACTION RULES:
1. Look for invoice numbers (may be labeled "Invoice #", "Bill #", "Document #", etc.)
2. Parse dates carefully - invoice date vs due date vs other dates
3. Extract complete vendor information including name and address
4. Capture all line items with descriptions, quantities, prices, and totals
5. Calculate or extract subtotals, taxes, and final totals
6. Identify currency (USD, EUR, etc.) if mentioned
7. Look for PO numbers and payment terms

CRITICAL: Return only valid JSON matching the exact schema structure.""",
    variables={"document_text": ""},
    output_schema=InvoiceData.model_json_schema(),
    examples=[
        {
            "input": {
                "document_text": "Bill #B-456-XYZ\nDate: March 10, 2023\nSupplier: Office Depot Inc\n789 Supply Ave\n\n5x Desk Chairs @ $180.00 = $900.00\n1x Conference Table @ $650.00 = $650.00\nSubtotal: $1,550.00\nTax: $124.00\nTotal: $1,674.00"
            },
            "output": {
                "invoice_number": "B-456-XYZ",
                "invoice_date": "2023-03-10",
                "due_date": None,
                "vendor": {
                    "name": "Office Depot Inc",
                    "address": "789 Supply Ave",
                    "phone": None,
                    "email": None,
                },
                "line_items": [
                    {
                        "description": "Desk Chairs",
                        "quantity": 5,
                        "unit_price": 180.0,
                        "total": 900.0,
                    },
                    {
                        "description": "Conference Table",
                        "quantity": 1,
                        "unit_price": 650.0,
                        "total": 650.0,
                    }
                ],
                "subtotal": 1550.0,
                "tax_amount": 124.0,
                "total_amount": 1674.0,
                "currency": None,
                "po_number": None,
                "payment_terms": None,
                "notes": None,
            },
        },
        {
            "input": {
                "document_text": "Bill #B-789\nIssued: 2024-02-20\nDue: 2024-03-20\nDataTech Solutions\n456 Oak Ave\nPhone: (555) 123-4567\n\n5x Database Setup @ $500.00 = $2,500.00\n10x Support Hours @ $150.00 = $1,500.00\n\nSubtotal: $4,000.00\nTax (8%): $320.00\nTotal: $4,320.00\nPO: PO-12345\nTerms: Net 30"
            },
            "output": {
                "invoice_number": "B-789",
                "invoice_date": "2024-02-20",
                "due_date": "2024-03-20",
                "vendor": {
                    "name": "DataTech Solutions",
                    "address": "456 Oak Ave",
                    "phone": "(555) 123-4567",
                    "email": None,
                },
                "line_items": [
                    {
                        "description": "Database Setup",
                        "quantity": 5,
                        "unit_price": 500.0,
                        "total": 2500.0,
                    },
                    {
                        "description": "Support Hours",
                        "quantity": 10,
                        "unit_price": 150.0,
                        "total": 1500.0,
                    },
                ],
                "subtotal": 4000.0,
                "tax_amount": 320.0,
                "total_amount": 4320.0,
                "currency": None,
                "po_number": "PO-12345",
                "payment_terms": "Net 30",
                "notes": None,
            },
        },
    ],
)


# Prompt specifically for scanned/OCR'd invoices (lower quality text)
invoice_extraction_ocr = Prompt(
    template="""You are processing an invoice that was extracted from a scanned image using OCR. 
The text may contain errors, missing characters, or formatting issues.

OCR EXTRACTED TEXT:
{document_text}

Your task is to extract structured data despite potential OCR errors:

COMMON OCR ERRORS TO HANDLE:
- "0" may appear as "O" or "D"
- "1" may appear as "l" or "I" 
- "5" may appear as "S"
- Decimal points may be missing or misplaced
- Currency symbols may be garbled

Be flexible with extraction but maintain accuracy. If text is unclear, use your best judgment.

IMPORTANT: 
- Fix obvious OCR errors when possible
- Use null for values you cannot determine with confidence
- Include confidence_notes for uncertain extractions
- Return only valid JSON matching the schema""",
    variables={"document_text": ""},
    output_schema=OCRInvoiceData.model_json_schema(),
    examples=[
        {
            "input": {
                "document_text": "lnv0ice #lNV-2O24-OO3\nDate: 2O24-Ol-2O\nFr0m: ACME C0rp\nl23 Main St\nlx S0ftware License $lOO.OO\nT0tal: $lOO.OO"
            },
            "output": {
                "invoice_number": "INV-2024-003",
                "invoice_date": "2024-01-20",
                "vendor": {
                    "name": "ACME Corp",
                    "address": "123 Main St",
                    "phone": None,
                    "email": None,
                },
                "line_items": [
                    {
                        "description": "Software License",
                        "quantity": 1,
                        "unit_price": 100.0,
                        "total": 100.0,
                    }
                ],
                "total_amount": 100.0,
                "currency": None,
                "confidence_notes": "Fixed OCR errors: 'lnv0ice' to 'Invoice', '0' to 'O' in numbers, 'l' to '1' in quantities",
            },
        }
    ],
)
