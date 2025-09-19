"""Production pipeline for document analysis with comprehensive processing.

This pipeline orchestrates the complete document analysis workflow,
from ingestion through analysis to report generation, with full
logging and error handling. Now supports serving deployment.
"""

from typing import Annotated, Optional

from models import DocumentAnalysis
from steps import (
    analyze_document_step,
    ingest_document_step,
    render_analysis_report_step,
)

from zenml import ArtifactConfig, Model, pipeline
from zenml.config import DockerSettings
from zenml.logger import get_logger

# Get ZenML logger for pipeline-level logging
logger = get_logger(__name__)


# Docker settings for reproducible pipeline execution
docker_settings = DockerSettings(
    requirements="requirements.txt",
    parent_image="zenmldocker/zenml:0.85.0-py3.12",
)


@pipeline(
    settings={"docker": docker_settings},
    enable_cache=False,  # Disable caching for serving
)
def doc_analyzer(
    content: Optional[str] = None,
    url: Optional[str] = None,
    path: Optional[str] = None,
    filename: Optional[str] = None,
    document_type: str = "text",
    analysis_type: str = "full",
) -> Annotated[
    DocumentAnalysis,
    ArtifactConfig(name="document_analysis", tags=["analysis", "serving"]),
]:
    """Complete document analysis pipeline with logging and error handling.

    This pipeline performs end-to-end document analysis including:
    1. Document ingestion from content/URL/path
    2. Content analysis (LLM-based or deterministic fallback)
    3. HTML report generation
    4. Returns analysis for serving deployment

    Args:
        content: Direct text content (optional)
        url: URL to download content from (optional)
        path: Path to file in artifact store or local filesystem (optional)
        filename: Name for the document (auto-generated if not provided)
        document_type: Type of document (text, markdown, report, article)
        analysis_type: Analysis depth (full, summary_only, etc.)

    Returns:
        DocumentAnalysis: Complete analysis results tagged for serving
    """
    logger.info(
        f"Starting document analysis pipeline "
        f"(type: {document_type}, analysis: {analysis_type})"
    )

    # Step 1: Ingest and validate document from various sources
    logger.info("Step 1/3: Ingesting document")
    document = ingest_document_step(
        content=content,
        url=url,
        path=path,
        filename=filename,
        document_type=document_type,
        analysis_type=analysis_type,
    )

    # Step 2: Perform analysis (LLM or deterministic)
    logger.info("Step 2/3: Analyzing document content")
    analysis = analyze_document_step(document)

    # Step 3: Generate HTML report (optional for serving)
    logger.info("Step 3/3: Rendering analysis report")
    render_analysis_report_step(analysis)

    logger.info(
        f"Document analysis pipeline completed successfully for: {filename or 'document'}"
    )

    # Return analysis for serving deployment
    return analysis
