"""Document ingestion and preprocessing steps for ZenML pipeline.

This module contains steps responsible for ingesting and preprocessing
document data before analysis. It handles different document types and
formats, preparing them for analysis.
"""

from models import DocumentRequest

from zenml import step
from zenml.logger import get_logger

# Get ZenML logger for consistent logging
logger = get_logger(__name__)


@step
def ingest_document_step(
    filename: str,
    content: str,
    document_type: str = "text",
    analysis_type: str = "full",
) -> DocumentRequest:
    """Ingest and validate document data for analysis.

    This step creates a structured DocumentRequest object from raw input data,
    validates the content, and logs relevant information for traceability.

    Args:
        filename: Name of the document being processed
        content: Raw text content of the document
        document_type: Type of document (text, markdown, report, article)
        analysis_type: Type of analysis to perform (full, summary_only, etc.)

    Returns:
        DocumentRequest: Structured document data ready for analysis

    Raises:
        ValueError: If content is empty or invalid
    """
    logger.info(f"Ingesting document: {filename}")

    # Validate input parameters
    if not content or not content.strip():
        error_msg = f"Document content is empty for file: {filename}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not filename:
        error_msg = "Filename cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Log document statistics for monitoring
    content_stats = {
        "character_count": len(content),
        "word_count": len(content.split()),
        "line_count": len(content.split("\n")),
        "document_type": document_type,
        "analysis_type": analysis_type,
    }

    logger.info(f"Document statistics: {content_stats}")

    # Create and return the document request
    document = DocumentRequest(
        filename=filename,
        content=content,
        document_type=document_type,
        analysis_type=analysis_type,
    )

    logger.info(f"Successfully ingested document: {filename}")
    return document
