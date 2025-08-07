"""Batch extraction step."""

from datetime import datetime
from typing import Any, Dict, List

from utils.api_utils import (
    call_openai_api,
    estimate_token_cost,
    parse_json_response,
)

from zenml import step
from zenml.prompts import Prompt, PromptResponse


@step
def extract_batch_data(
    documents: List[Dict[str, Any]],
    extraction_prompt: Prompt,
    model_name: str = "gpt-4",
) -> List[PromptResponse]:
    """Extract data from multiple documents using enhanced prompt/response artifacts.

    Args:
        documents: List of dictionaries containing document data
        extraction_prompt: ZenML Prompt artifact for extraction
        model_name: Name of the LLM model to use

    Returns:
        List of PromptResponse artifacts containing extracted data and metadata
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
            start_time = datetime.now()
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
            parsing_successful = extracted_data is not None

            # Calculate cost
            estimated_cost = estimate_token_cost(
                api_response["usage"], model_name
            )

            # Create PromptResponse artifact
            prompt_response = PromptResponse(
                content=api_response["content"],
                parsed_output=extracted_data,
                model_name=model_name,
                temperature=0.1,
                max_tokens=2000,
                prompt_tokens=api_response["usage"].get("prompt_tokens"),
                completion_tokens=api_response["usage"].get(
                    "completion_tokens"
                ),
                total_tokens=api_response["usage"].get("total_tokens"),
                total_cost=estimated_cost,
                validation_passed=parsing_successful,
                created_at=start_time,
                response_time_ms=api_response.get("response_time_ms"),
                metadata={
                    "document_path": doc["file_path"],
                    "finish_reason": api_response.get("finish_reason"),
                    "prompt_type": str(extraction_prompt.prompt_type),
                    "has_schema": extraction_prompt.output_schema is not None,
                    "example_count": len(extraction_prompt.examples),
                },
            )

            # Add validation errors if parsing failed
            if not parsing_successful:
                prompt_response.add_validation_error(
                    f"Failed to parse JSON from LLM response: {api_response['content'][:200]}..."
                )

            results.append(prompt_response)

            # Track total cost
            total_cost += estimated_cost
            print(
                f"  Extracted data successfully (cost: ${estimated_cost:.4f})"
            )

        except Exception as e:
            print(f"  Failed to extract from {doc['file_path']}: {e}")

            # Create error PromptResponse
            error_response = PromptResponse(
                content=f"Error during processing: {str(e)}",
                model_name=model_name,
                validation_passed=False,
                created_at=datetime.now(),
                metadata={
                    "document_path": doc["file_path"],
                    "error": str(e),
                    "failed": True,
                },
            )
            error_response.add_validation_error(str(e))
            results.append(error_response)

    print(
        f"Batch processing complete. Total estimated cost: ${total_cost:.4f}"
    )
    return results
