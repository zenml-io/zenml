"""Document processing utilities."""

import tempfile
from pathlib import Path
from typing import Any, Dict

# Optional imports - gracefully handle missing dependencies
try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pytesseract
    from PIL import Image

    HAS_OCR = True
except ImportError:
    HAS_OCR = False


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    if not HAS_PYMUPDF:
        raise ImportError(
            "PyMuPDF (fitz) is required for PDF processing. Install with: pip install PyMuPDF"
        )

    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF {file_path}: {e}")


def extract_text_from_image(file_path: str) -> str:
    """Extract text from image using Tesseract OCR."""
    if not HAS_OCR:
        raise ImportError(
            "Tesseract and Pillow are required for OCR processing. Install with: pip install pytesseract pillow"
        )

    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to extract text from image {file_path}: {e}")


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        raise ValueError(f"Failed to read text file {file_path}: {e}")


def extract_text_from_bytes(content: bytes, file_extension: str) -> str:
    """Extract text from file bytes based on extension."""
    with tempfile.NamedTemporaryFile(
        suffix=file_extension, delete=False
    ) as tmp_file:
        tmp_file.write(content)
        tmp_file.flush()

        try:
            if file_extension.lower() == ".pdf":
                return extract_text_from_pdf(tmp_file.name)
            elif file_extension.lower() in [
                ".png",
                ".jpg",
                ".jpeg",
                ".tiff",
                ".bmp",
            ]:
                return extract_text_from_image(tmp_file.name)
            else:
                raise ValueError(
                    f"Unsupported file extension: {file_extension}"
                )
        finally:
            Path(tmp_file.name).unlink(missing_ok=True)


def preprocess_document_text(text: str) -> str:
    """Clean and preprocess extracted text."""
    if not text:
        return ""

    # Remove excessive whitespace
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Join lines with single newlines
    cleaned_text = "\n".join(lines)

    # Remove multiple consecutive newlines
    while "\n\n\n" in cleaned_text:
        cleaned_text = cleaned_text.replace("\n\n\n", "\n\n")

    return cleaned_text


def detect_document_type(text: str) -> str:
    """Simple document type detection based on content."""
    text_lower = text.lower()

    # Check for invoice indicators
    invoice_keywords = [
        "invoice",
        "bill to",
        "amount due",
        "invoice number",
        "invoice #",
    ]
    if any(keyword in text_lower for keyword in invoice_keywords):
        return "invoice"

    # Check for contract indicators
    contract_keywords = [
        "agreement",
        "contract",
        "party",
        "whereas",
        "terms and conditions",
    ]
    if any(keyword in text_lower for keyword in contract_keywords):
        return "contract"

    # Default to general document
    return "general"


def create_document_metadata(file_path: str, text: str) -> Dict[str, Any]:
    """Create metadata for a processed document."""
    return {
        "file_path": file_path,
        "file_name": Path(file_path).name,
        "file_extension": Path(file_path).suffix,
        "text_length": len(text),
        "line_count": len(text.split("\n")),
        "word_count": len(text.split()),
        "detected_type": detect_document_type(text),
        "has_content": bool(text.strip()),
    }


def validate_extraction_requirements(text: str, min_length: int = 50) -> bool:
    """Validate that extracted text meets minimum requirements for processing."""
    if not text or len(text.strip()) < min_length:
        return False

    # Check for common extraction issues
    if text.count("�") > len(text) * 0.1:  # Too many replacement characters
        return False

    return True
