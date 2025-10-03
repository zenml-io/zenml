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

from zenml import ArtifactConfig, pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    requirements="requirements.txt",
    environment={
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
    },
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

    Returns:
        DocumentAnalysis: Complete analysis results tagged for serving
    """
    # Ingest and validate document from various sources
    document = ingest_document_step(
        content=content,
        url=url,
        path=path,
        filename=filename,
        document_type=document_type,
    )

    # Perform analysis (LLM or deterministic)
    analysis = analyze_document_step(document)

    # Generate HTML report (optional for serving)
    render_analysis_report_step(analysis)

    # Return analysis for serving deployment
    return analysis
