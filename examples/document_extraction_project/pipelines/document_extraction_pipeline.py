"""Main document extraction pipeline."""

from typing import Any, Dict, List

from steps.extract_batch_data import extract_batch_data
from steps.filter_processable_documents import filter_processable_documents
from steps.process_document_batch import process_document_batch
from steps.validate_batch_results import validate_batch_results

from zenml import pipeline


@pipeline(enable_cache=False)
def document_extraction_pipeline(
    file_paths: List[str],
    extraction_prompt: str,
    model_name: str = "gpt-4",
    min_text_length: int = 100,
) -> Dict[str, Any]:
    """Complete document extraction pipeline.

    Args:
        file_paths: List of paths to documents to process (can be remote paths)
        extraction_prompt: Prompt template string for extraction
        model_name: LLM model to use (default: gpt-4)
        min_text_length: Minimum text length to process document

    Returns:
        Validation results with extracted data and quality metrics
    """
    # Step 1: Process documents and extract text using artifact store
    processed_documents = process_document_batch(file_paths)

    # Step 2: Filter documents with sufficient text
    processable_documents = filter_processable_documents(
        processed_documents, min_text_length
    )

    # Step 3: Extract structured data using LLM
    extraction_results = extract_batch_data(
        processable_documents, extraction_prompt, model_name
    )

    # Step 4: Validate extracted data
    validation_results = validate_batch_results(extraction_results)

    return validation_results
