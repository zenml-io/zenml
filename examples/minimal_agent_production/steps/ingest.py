"""Document ingestion and preprocessing steps for ZenML pipeline.

This module contains steps responsible for ingesting and preprocessing
document data before analysis. It handles different document types and
formats, preparing them for analysis.
"""

import os
from typing import Annotated, Optional
from urllib.parse import urlparse

import requests
from constants import DEFAULT_DOC_TYPE, EXTENSION_TO_TYPE, URL_TIMEOUT_S
from models import DocumentRequest

from zenml import step
from zenml.artifact_stores import BaseArtifactStore
from zenml.client import Client


@step
def ingest_document_step(
    content: Optional[str] = None,
    url: Optional[str] = None,
    path: Optional[str] = None,
    filename: Optional[str] = None,
    document_type: str = DEFAULT_DOC_TYPE,
) -> Annotated[DocumentRequest, "Documents"]:
    """Ingest and validate document data for analysis from multiple sources.

    This step creates a structured DocumentRequest object from various input sources:
    1. Direct content (string)
    2. URL (downloads content from web)
    3. Path (loads from artifact store or local filesystem)

    Args:
        content: Direct text content (optional)
        url: URL to download content from (optional)
        path: Path to file in artifact store or local filesystem (optional)
        filename: Name for the document (auto-generated if not provided)
        document_type: Type of document (text, markdown, report, article)

    Returns:
        DocumentRequest: Structured document data ready for analysis

    Raises:
        ValueError: If no content source is provided or content is invalid
    """
    # Determine input source and extract content
    document_content = ""
    actual_filename = filename

    if content:
        document_content = content
        if not actual_filename:
            actual_filename = "direct_input.txt"
    elif url:
        document_content = _download_from_url(url)
        if not actual_filename:
            # Extract filename from URL
            parsed_url = urlparse(url)
            actual_filename = (
                os.path.basename(parsed_url.path) or "downloaded_content.txt"
            )
    elif path:
        document_content = _load_from_path(path)
        if not actual_filename:
            actual_filename = os.path.basename(path)
    else:
        error_msg = (
            "No content source provided. Must specify content, url, or path."
        )
        raise ValueError(error_msg)

    # Validate content
    if not document_content or not document_content.strip():
        error_msg = (
            f"Document content is empty after processing: {actual_filename}"
        )
        raise ValueError(error_msg)

    # Optionally infer document type from filename extension if not explicitly set beyond the default
    doc_type = document_type
    if actual_filename:
        try:
            ext = (
                actual_filename.rsplit(".", 1)[-1].lower()
                if "." in actual_filename
                else None
            )
            if doc_type == DEFAULT_DOC_TYPE and ext:
                doc_type = EXTENSION_TO_TYPE.get(ext, DEFAULT_DOC_TYPE)
        except Exception:
            # If inference fails, fall back to provided/default type
            doc_type = document_type

    # Create and return the document request
    document = DocumentRequest(
        filename=actual_filename,
        content=document_content,
        document_type=doc_type,
    )

    return document


def _download_from_url(url: str) -> str:
    """Download content from a URL.

    Args:
        url: URL to download from

    Returns:
        Downloaded content as string

    Raises:
        ValueError: If download fails or content is invalid
    """
    try:
        response = requests.get(url, timeout=URL_TIMEOUT_S)
        response.raise_for_status()

        # Handle different content types
        content_type = response.headers.get("content-type", "").lower()

        if "html" in content_type:
            # Basic HTML text extraction (you might want to use BeautifulSoup for better parsing)
            import re

            # Simple HTML tag removal
            clean_text = re.sub(r"<[^>]+>", "", response.text)
            return clean_text
        elif "text" in content_type or "json" in content_type:
            return response.text
        else:
            # For binary content, return a placeholder
            return f"[Binary content downloaded from {url}, {len(response.content)} bytes]"

    except Exception as e:
        error_msg = f"Failed to download from URL {url}: {str(e)}"
        raise ValueError(error_msg)


def _load_from_path(path: str) -> str:
    """Load content from a file path using ZenML artifact store interface.

    Args:
        path: Path to the file (can be local or artifact store path)

    Returns:
        File content as string

    Raises:
        ValueError: If file cannot be read or doesn't exist
    """
    try:
        client = Client()
        artifact_store: BaseArtifactStore = client.active_stack.artifact_store

        # Check if path exists in artifact store
        if artifact_store.exists(path):
            # Read file from artifact store
            with artifact_store.open(path, "r") as f:
                file_content: str = f.read()
            return file_content

        # Try local filesystem
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                local_content: str = f.read()
            return local_content

        error_msg = (
            f"File not found in artifact store or local filesystem: {path}"
        )
        raise ValueError(error_msg)

    except Exception as e:
        error_msg = f"Failed to load file from path {path}: {str(e)}"
        raise ValueError(error_msg)
