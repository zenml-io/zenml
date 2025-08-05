"""Batch document processing step."""

from pathlib import Path
from typing import Any, Dict, List

from utils.document_utils import (
    create_document_metadata,
    extract_text_from_bytes,
    preprocess_document_text,
    validate_extraction_requirements,
)

from zenml import step
from zenml.client import Client


@step
def process_document_batch(file_paths: List[str]) -> List[Dict[str, Any]]:
    """Process multiple documents in batch using ZenML artifact store.

    Args:
        file_paths: List of paths to documents to process

    Returns:
        List of processed document data dictionaries
    """
    # Get active artifact store for file access
    client = Client()
    artifact_store = client.active_stack.artifact_store

    results = []
    print(f"Processing {len(file_paths)} files...")

    for file_path in file_paths:
        try:
            # Handle both relative and absolute paths
            file_path_obj = Path(file_path)

            # If it's a relative path, try to find it in the artifact store
            # If it's an absolute path, use it directly
            if file_path_obj.is_absolute():
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"Document not found: {file_path}")
                # Read directly from filesystem for absolute paths
                file_content = file_path_obj.read_bytes()
            else:
                # Try artifact store for relative paths
                if artifact_store.exists(file_path):
                    with artifact_store.open(file_path, "rb") as f:
                        file_content = f.read()
                else:
                    # Fallback to local file system
                    local_path = Path.cwd() / file_path
                    if local_path.exists():
                        file_content = local_path.read_bytes()
                    else:
                        raise FileNotFoundError(
                            f"Document not found: {file_path}"
                        )

            # Get file extension to determine processing method
            file_extension = file_path_obj.suffix.lower()

            # Extract text based on file type
            if file_extension == ".pdf":
                raw_text = extract_text_from_bytes(
                    file_content, file_extension
                )
            elif file_extension in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
                raw_text = extract_text_from_bytes(
                    file_content, file_extension
                )
            elif file_extension in [".txt", ".text"]:
                raw_text = file_content.decode("utf-8")
            else:
                raise ValueError(
                    f"Unsupported file type: {file_extension}. "
                    f"Supported: .pdf, .txt, .png, .jpg, .jpeg"
                )

            # Clean and preprocess text
            cleaned_text = preprocess_document_text(raw_text)

            # Validate extraction quality
            if not validate_extraction_requirements(cleaned_text):
                raise ValueError(
                    f"Extracted text quality is too low: {file_path}"
                )

            # Create metadata
            metadata = create_document_metadata(file_path, cleaned_text)

            results.append(
                {
                    "file_path": file_path,
                    "original_text": raw_text,
                    "cleaned_text": cleaned_text,
                    "metadata": metadata,
                }
            )

        except Exception as e:
            print(f"Failed to process {file_path}: {e}")
            # Add failed document with error info
            results.append(
                {
                    "file_path": file_path,
                    "original_text": "",
                    "cleaned_text": "",
                    "metadata": {"error": str(e), "processed": False},
                }
            )

    return results
