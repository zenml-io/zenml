"""Document filtering step."""

from typing import Any, Dict, List

from zenml import step


@step
def filter_processable_documents(
    documents: List[Dict[str, Any]], min_text_length: int = 100
) -> List[Dict[str, Any]]:
    """Filter documents that have sufficient text for extraction.

    Args:
        documents: List of dictionaries containing document data
        min_text_length: Minimum text length to consider a document processable

    Returns:
        List of dictionaries containing processable documents
    """
    processable = []

    for doc in documents:
        if (
            doc.get("cleaned_text")
            and len(doc["cleaned_text"]) >= min_text_length
            and not doc.get("metadata", {}).get("error")
        ):
            processable.append(doc)
        else:
            print(
                f"Skipping document due to insufficient text: {doc.get('file_path')}"
            )

    print(
        f"Filtered {len(processable)} processable documents from {len(documents)} total"
    )
    return processable
