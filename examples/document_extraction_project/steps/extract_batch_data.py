"""Batch extraction step."""

from typing import Any, Dict, List

from utils.api_utils import (
    call_openai_api,
    estimate_token_cost,
    parse_json_response,
)

from zenml import step
from zenml.prompts import Prompt


@step
def extract_batch_data(
    documents: List[Dict[str, Any]],
    extraction_prompt: Prompt,
    model_name: str = "gpt-4",
) -> List[Dict[str, Any]]:
    """Extract data from multiple documents.

    Args:
        documents: List of dictionaries containing document data
        extraction_prompt: ZenML Prompt artifact for extraction
        model_name: Name of the LLM model to use

    Returns:
        List of dictionaries containing extracted data, processing metadata, and raw LLM response
    """
    results = []
    total_cost = 0.0

    for i, doc in enumerate(documents):
        try:
            print(
                f"Processing document {i + 1}/{len(documents)}: {doc['file_path']}"
            )

            # Format prompt with document text
            try:
                formatted_prompt = extraction_prompt.format(
                    document_text=doc["cleaned_text"]
                )
            except KeyError as e:
                raise ValueError(
                    f"Prompt formatting failed - missing variable: {e}"
                )

            # Call LLM API
            try:
                api_response = call_openai_api(
                    prompt=formatted_prompt,
                    model=model_name,
                    temperature=0.1,
                    max_tokens=2000,
                )
            except Exception as e:
                raise RuntimeError(f"LLM API call failed: {e}")

            # Parse JSON response
            extracted_data = parse_json_response(api_response["content"])
            if extracted_data is None:
                raise ValueError(
                    f"Failed to parse JSON from LLM response: {api_response['content'][:200]}..."
                )

            # Calculate cost
            estimated_cost = estimate_token_cost(
                api_response["usage"], model_name
            )

            result = {
                "file_path": doc["file_path"],
                "extracted_data": extracted_data,
                "raw_llm_response": api_response["content"],
                "processing_metadata": {
                    "model_used": model_name,
                    "prompt_type": extraction_prompt.prompt_type,
                    "prompt_variables": list(extraction_prompt.variables.keys()),
                    "token_usage": api_response["usage"],
                    "response_time_ms": api_response["response_time_ms"],
                    "estimated_cost_usd": estimated_cost,
                    "finish_reason": api_response["finish_reason"],
                },
            }

            results.append(result)

            # Track total cost
            cost = result["processing_metadata"]["estimated_cost_usd"]
            total_cost += cost
            print(f"  Extracted data successfully (cost: ${cost:.4f})")

        except Exception as e:
            print(f"  Failed to extract from {doc['file_path']}: {e}")
            results.append(
                {
                    "file_path": doc["file_path"],
                    "extracted_data": None,
                    "error": str(e),
                    "processing_metadata": {"failed": True},
                }
            )

    print(
        f"Batch processing complete. Total estimated cost: ${total_cost:.4f}"
    )
    return results
