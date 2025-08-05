"""Batch validation step."""

from datetime import datetime
from typing import Any, Dict, List, Type

from pydantic import BaseModel, ValidationError
from schemas.invoice_schema import InvoiceData

from zenml import step


@step
def validate_batch_results(
    extraction_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate batch of extraction results.

    Args:
        extraction_results: List of dictionaries containing extracted data

    Returns:
        Dictionary containing validation results
    """
    print(f"Validating {len(extraction_results)} extraction results...")
    expected_schema = InvoiceData  # Use InvoiceData as default schema
    validated_results = []
    summary_stats = {
        "total_documents": len(extraction_results),
        "successful_extractions": 0,
        "schema_valid_count": 0,
        "average_completeness": 0.0,
        "average_confidence": 0.0,
        "total_errors": 0,
        "total_warnings": 0,
    }

    for result in extraction_results:
        if result.get("extracted_data") is not None:
            validated = _validate_single_result(result, expected_schema)
            validated_results.append(validated)

            if validated["is_valid"]:
                summary_stats["successful_extractions"] += 1
            if validated["schema_valid"]:
                summary_stats["schema_valid_count"] += 1

            summary_stats["total_errors"] += len(validated["errors"])
            summary_stats["total_warnings"] += len(validated["warnings"])

        else:
            # Failed extraction
            validated_results.append(
                {
                    "file_path": result.get("file_path"),
                    "is_valid": False,
                    "schema_valid": False,
                    "validated_data": None,
                    "errors": [result.get("error", "Extraction failed")],
                    "warnings": [],
                    "quality_metrics": {"overall_quality": 0.0},
                }
            )

    # Calculate averages
    valid_results = [r for r in validated_results if r["quality_metrics"]]
    if valid_results:
        summary_stats["average_completeness"] = sum(
            r["quality_metrics"].get("field_completeness", 0)
            for r in valid_results
        ) / len(valid_results)
        summary_stats["average_confidence"] = sum(
            r["quality_metrics"].get("confidence_score", 0)
            for r in valid_results
        ) / len(valid_results)

    summary_stats["success_rate"] = (
        summary_stats["successful_extractions"]
        / summary_stats["total_documents"]
        if summary_stats["total_documents"] > 0
        else 0.0
    )
    summary_stats["schema_compliance_rate"] = (
        summary_stats["schema_valid_count"] / summary_stats["total_documents"]
        if summary_stats["total_documents"] > 0
        else 0.0
    )

    return {
        "validated_results": validated_results,
        "summary_stats": summary_stats,
    }


def _validate_single_result(
    extraction_result: Dict[str, Any], expected_schema: Type[BaseModel]
) -> Dict[str, Any]:
    """Validate a single extraction result."""
    validation_errors = []
    validation_warnings = []

    extracted_data = extraction_result.get("extracted_data", {})

    # 1. Schema validation
    try:
        validated_data = expected_schema(**extracted_data)
        schema_valid = True
        validated_dict = validated_data.model_dump()
    except ValidationError as e:
        schema_valid = False
        validated_dict = extracted_data
        for error in e.errors():
            field = ".".join([str(x) for x in error["loc"]])
            validation_errors.append(
                f"Schema error in {field}: {error['msg']}"
            )
    except Exception as e:
        schema_valid = False
        validated_dict = extracted_data
        validation_errors.append(f"Unexpected validation error: {str(e)}")

    # 2. Business logic validation (if schema validation passed)
    if schema_valid and isinstance(validated_dict, dict):
        # Amount validations
        total_amount = validated_dict.get("total_amount")
        if total_amount is not None and total_amount <= 0:
            validation_warnings.append("Total amount should be positive")

        subtotal = validated_dict.get("subtotal")
        tax_amount = validated_dict.get("tax_amount")
        if subtotal and tax_amount and total_amount:
            calculated_total = subtotal + tax_amount
            if abs(calculated_total - total_amount) > 0.01:
                validation_warnings.append(
                    f"Total amount mismatch: {total_amount} vs calculated {calculated_total:.2f}"
                )

        # Line items validation
        line_items = validated_dict.get("line_items", [])
        for i, item in enumerate(line_items):
            if isinstance(item, dict):
                quantity = item.get("quantity")
                unit_price = item.get("unit_price")
                total = item.get("total")

                if quantity and unit_price and total:
                    calculated_total = quantity * unit_price
                    if abs(calculated_total - total) > 0.01:
                        validation_warnings.append(
                            f"Line item {i + 1} total mismatch: {total} vs calculated {calculated_total:.2f}"
                        )

        # Date validations
        invoice_date = validated_dict.get("invoice_date")
        due_date = validated_dict.get("due_date")
        if invoice_date and due_date:
            if isinstance(invoice_date, str):
                try:
                    invoice_date = datetime.fromisoformat(invoice_date).date()
                except ValueError:
                    pass
            if isinstance(due_date, str):
                try:
                    due_date = datetime.fromisoformat(due_date).date()
                except ValueError:
                    pass

            if hasattr(invoice_date, "year") and hasattr(due_date, "year"):
                if due_date < invoice_date:
                    validation_warnings.append(
                        "Due date is before invoice date"
                    )

    # 3. Calculate quality scores
    completeness_score = _calculate_field_completeness(extracted_data)
    confidence_score = _calculate_confidence_score(extraction_result)

    return {
        "file_path": extraction_result.get("file_path"),
        "is_valid": len(validation_errors) == 0,
        "schema_valid": schema_valid,
        "validated_data": validated_dict,
        "errors": validation_errors,
        "warnings": validation_warnings,
        "quality_metrics": {
            "field_completeness": completeness_score,
            "schema_compliance": 1.0 if schema_valid else 0.0,
            "confidence_score": confidence_score,
            "overall_quality": (
                completeness_score
                + (1.0 if schema_valid else 0.0)
                + confidence_score
            )
            / 3,
        },
        "processing_metadata": extraction_result.get(
            "processing_metadata", {}
        ),
    }


def _calculate_field_completeness(data: Dict[str, Any]) -> float:
    """Calculate what percentage of expected fields are populated."""
    if not data:
        return 0.0

    def count_fields(obj, depth=0):
        """Recursively count fields, giving less weight to deeply nested fields."""
        if depth > 3:  # Prevent infinite recursion
            return 0, 0

        non_null_count = 0
        total_count = 0

        if isinstance(obj, dict):
            for value in obj.values():
                total_count += 1
                if value is not None and value != "" and value != []:
                    non_null_count += 1

                # Recursively count nested structures with reduced weight
                if isinstance(value, (dict, list)) and depth < 2:
                    nested_non_null, nested_total = count_fields(
                        value, depth + 1
                    )
                    non_null_count += (
                        nested_non_null * 0.5
                    )  # Reduce weight of nested fields
                    total_count += nested_total * 0.5

        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)) and depth < 2:
                    nested_non_null, nested_total = count_fields(
                        item, depth + 1
                    )
                    non_null_count += nested_non_null * 0.5
                    total_count += nested_total * 0.5

        return non_null_count, total_count

    non_null_count, total_count = count_fields(data)
    return non_null_count / total_count if total_count > 0 else 0.0


def _calculate_confidence_score(extraction_result: Dict[str, Any]) -> float:
    """Calculate confidence score based on extraction metadata."""
    metadata = extraction_result.get("processing_metadata", {})

    # Base confidence from successful extraction
    confidence = 0.5

    # Boost confidence if LLM finished normally
    if metadata.get("finish_reason") == "stop":
        confidence += 0.2

    # Reduce confidence if fallback was used
    if metadata.get("used_fallback"):
        confidence -= 0.2

    # Adjust based on response length (very short responses are suspicious)
    raw_response = extraction_result.get("raw_llm_response", "")
    if len(raw_response) > 100:
        confidence += 0.1
    elif len(raw_response) < 50:
        confidence -= 0.2

    # Adjust based on token usage (reasonable usage indicates good response)
    token_usage = metadata.get("token_usage", {})
    completion_tokens = token_usage.get("completion_tokens", 0)
    if 50 < completion_tokens < 1000:  # Reasonable range
        confidence += 0.1

    return max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
