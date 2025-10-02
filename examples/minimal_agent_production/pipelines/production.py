"""Production pipeline for document analysis with comprehensive processing.

This pipeline orchestrates the complete document analysis workflow,
from ingestion through analysis to report generation, with full
logging and error handling.
"""

from steps import (
    analyze_document_step,
    ingest_document_step,
    render_analysis_report_step,
)

from zenml import Model, pipeline
from zenml.config import DockerSettings
from zenml.logger import get_logger

# Get ZenML logger for pipeline-level logging
logger = get_logger(__name__)


# Docker settings for reproducible pipeline execution
docker_settings = DockerSettings(
    requirements="requirements.txt",
    python_package_installer="uv",
)


@pipeline(
    settings={"docker": docker_settings},
    model=Model(name="document_analysis_agent", version="production"),
)
def document_analysis_pipeline(
    filename: str,
    content: str,
    document_type: str = "text",
    analysis_type: str = "full",
) -> None:
    """Complete document analysis pipeline with logging and error handling.

    This pipeline performs end-to-end document analysis including:
    1. Document ingestion and validation
    2. Content analysis (LLM-based or deterministic fallback)
    3. HTML report generation

    Args:
        filename: Name of the document being processed
        content: Raw document content to analyze
        document_type: Type of document (text, markdown, report, article)
        analysis_type: Analysis depth (full, summary_only, etc.)
    """
    logger.info(
        f"Starting document analysis pipeline for: {filename} "
        f"(type: {document_type}, analysis: {analysis_type})"
    )

    # Step 1: Ingest and validate document
    logger.info("Step 1/3: Ingesting document")
    document = ingest_document_step(
        filename=filename,
        content=content,
        document_type=document_type,
        analysis_type=analysis_type,
    )

    # Step 2: Perform analysis (LLM or deterministic)
    logger.info("Step 2/3: Analyzing document content")
    analysis = analyze_document_step(document)

    # Step 3: Generate HTML report
    logger.info("Step 3/3: Rendering analysis report")
    render_analysis_report_step(analysis)

    logger.info(
        f"Document analysis pipeline completed successfully for: {filename}"
    )
