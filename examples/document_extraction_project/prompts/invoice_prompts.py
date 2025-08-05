"""Invoice extraction prompts for ZenML."""

from prompts.base_prompt import Prompt

# Basic invoice extraction prompt
invoice_extraction_v1 = Prompt(
    template="""You are an expert invoice processing system. Extract structured data from this invoice text.

INVOICE TEXT:
{document_text}

Extract the following information and return as valid JSON:
{{
    "invoice_number": "string or null",
    "invoice_date": "YYYY-MM-DD or null",
    "due_date": "YYYY-MM-DD or null",
    "vendor": {{
        "name": "string or null",
        "address": "string or null", 
        "phone": "string or null",
        "email": "string or null"
    }},
    "line_items": [
        {{
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total": number
        }}
    ],
    "subtotal": number or null,
    "tax_amount": number or null,
    "total_amount": number or null,
    "currency": "string or null",
    "po_number": "string or null",
    "payment_terms": "string or null",
    "notes": "string or null"
}}

CRITICAL REQUIREMENTS:
1. Return ONLY valid JSON - no explanations or extra text
2. Use null for missing values
3. Dates must be in YYYY-MM-DD format
4. Numbers should be numeric types, not strings
5. Line items must be an array of objects

Extract the data now:""",
    variables=["document_text"]
)


# Enhanced invoice extraction prompt with examples
invoice_extraction_v2 = Prompt(
    template="""You are an expert invoice processing AI. Extract structured data from invoices with high accuracy.

INVOICE TEXT:
{document_text}

EXAMPLE OUTPUT FORMAT:
For an invoice containing:
- Invoice #INV-2024-001 dated January 15, 2024
- From TechSupply Corp at 123 Main St
- 2x Laptops at $999 each = $1,998
- Tax: $159.84, Total: $2,157.84

Extract as:
{{
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "due_date": null,
    "vendor": {{
        "name": "TechSupply Corp",
        "address": "123 Main St",
        "phone": null,
        "email": null
    }},
    "line_items": [
        {{
            "description": "Laptops",
            "quantity": 2,
            "unit_price": 999.00,
            "total": 1998.00
        }}
    ],
    "subtotal": 1998.00,
    "tax_amount": 159.84,
    "total_amount": 2157.84,
    "currency": "USD",
    "po_number": null,
    "payment_terms": null,
    "notes": null
}}

EXTRACTION RULES:
1. Look for invoice numbers (may be labeled "Invoice #", "Bill #", "Document #", etc.)
2. Parse dates carefully - invoice date vs due date vs other dates
3. Extract complete vendor information including name and address
4. Capture all line items with descriptions, quantities, prices, and totals
5. Calculate or extract subtotals, taxes, and final totals
6. Identify currency (USD, EUR, etc.) if mentioned
7. Look for PO numbers and payment terms

CRITICAL: Return only valid JSON matching the exact structure above.""",
    variables=["document_text"]
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

Return JSON in this exact format:
{{
    "invoice_number": "string or null",
    "invoice_date": "YYYY-MM-DD or null", 
    "vendor": {{
        "name": "string or null",
        "address": "string or null"
    }},
    "line_items": [
        {{
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total": number
        }}
    ],
    "total_amount": number or null,
    "currency": "string or null",
    "confidence_notes": "string describing any uncertain extractions"
}}

IMPORTANT: 
- Fix obvious OCR errors when possible
- Use null for values you cannot determine with confidence
- Include confidence_notes for uncertain extractions
- Return only valid JSON""",
    variables=["document_text"]
)
