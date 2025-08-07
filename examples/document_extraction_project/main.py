"""Document extraction pipeline runner."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from pipelines.document_extraction_pipeline import document_extraction_pipeline
from prompt.invoice_prompts import (
    invoice_extraction_ocr,
    invoice_extraction_v2,
)
from utils.api_utils import validate_api_setup


def setup_environment() -> None:
    """Set up the environment and validate API access."""
    print("🔧 Setting up environment...")

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print(
            "Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'"
        )
        sys.exit(1)

    try:
        validate_api_setup()
        print("✅ API access validated")
    except Exception as e:
        if "quota" in str(e) or "429" in str(e):
            print("⚠️  API quota exceeded, but proceeding")
        elif "proxies" in str(e):
            print("⚠️  OpenAI client version issue, but proceeding")
        else:
            print(f"❌ API validation failed: {e}")
            sys.exit(1)

    print("✅ Environment setup complete")


def setup_prompt_artifacts() -> None:
    """Setup and validate prompt artifacts."""
    print("🎯 Setting up prompt artifacts...")

    try:
        test_text = "Sample document text for validation"
        formatted = invoice_extraction_v2.format(document_text=test_text)

        if len(formatted) <= len(test_text):
            raise ValueError("Prompt formatting appears to be broken")

        print("✅ Prompt artifacts ready")

    except Exception as e:
        print(f"❌ Failed to setup prompt artifacts: {e}")
        sys.exit(1)


def get_file_paths(document_path: str) -> List[str]:
    """Get list of file paths to process."""
    path = Path(document_path)

    if path.is_dir():
        # Find all supported document files in directory
        file_paths = []
        for ext in [".pdf", ".png", ".jpg", ".jpeg", ".txt"]:
            file_paths.extend(path.glob(f"*{ext}"))
        return [str(p) for p in file_paths]
    else:
        # Single file
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {document_path}")
        return [str(path)]


def select_prompt(document_type: str, extraction_method: str = "standard"):
    """Select appropriate prompt based on document type and method."""
    if document_type == "invoice" and extraction_method == "ocr":
        return invoice_extraction_ocr
    return invoice_extraction_v2


def print_results_summary(results: Dict[str, Any]) -> None:
    """Print a summary of extraction results."""
    print("\n" + "=" * 50)
    print("📊 EXTRACTION RESULTS")
    print("=" * 50)

    summary = results.get("summary_stats", {})

    print(f"📄 Documents: {summary.get('total_documents', 0)}")
    print(f"✅ Successful: {summary.get('successful_extractions', 0)}")
    print(f"🎯 Success rate: {summary.get('success_rate', 0):.1%}")
    print(
        f"📋 Schema compliance: {summary.get('schema_compliance_rate', 0):.1%}"
    )

    if summary.get("total_errors", 0) > 0:
        print(f"❌ Errors: {summary.get('total_errors', 0)}")
    if summary.get("total_warnings", 0) > 0:
        print(f"⚠️  Warnings: {summary.get('total_warnings', 0)}")


def print_individual_results(
    results: dict, show_details: bool = False
) -> None:
    """Print individual document results."""
    validated_results = results.get("validated_results", [])

    print("\n📋 Individual Results:")

    for i, result in enumerate(validated_results, 1):
        file_path = result.get("file_path", "Unknown")
        file_name = Path(file_path).name

        status = "✅" if result.get("is_valid") else "❌"
        quality = result.get("quality_metrics", {}).get("overall_quality", 0)

        print(f"{i}. {file_name} {status} (Quality: {quality:.1%})")

        if show_details and result.get("errors"):
            for error in result["errors"]:
                print(f"   - {error}")


def save_results_to_file(results: dict, output_path: str) -> None:
    """Save results to JSON file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"💾 Results saved to: {output_file}")


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Run document extraction pipeline"
    )
    parser.add_argument(
        "--document", "-d", required=True, help="Path to document or directory"
    )
    parser.add_argument(
        "--type",
        "-t",
        default="invoice",
        choices=["invoice", "contract"],
        help="Document type",
    )
    parser.add_argument(
        "--method",
        "-m",
        default="standard",
        choices=["standard", "ocr"],
        help="Extraction method",
    )
    parser.add_argument("--model", default="gpt-4", help="LLM model to use")
    parser.add_argument("--output", "-o", help="Output file for results")
    parser.add_argument(
        "--show-details",
        action="store_true",
        help="Show detailed error messages",
    )

    args = parser.parse_args()

    try:
        setup_environment()
        setup_prompt_artifacts()

        file_paths = get_file_paths(args.document)
        file_paths = [str(Path(fp).resolve()) for fp in file_paths]
        print(f"\n📁 Found {len(file_paths)} file(s) to process")

        extraction_prompt = select_prompt(args.type, args.method)
        print(f"🎯 Using prompt: {args.type} ({args.method})")

        print(f"\n🚀 Starting extraction with {args.model}...")

        pipeline_run = document_extraction_pipeline(
            file_paths=file_paths,
            extraction_prompt=extraction_prompt,
            model_name=args.model,
        )

        try:
            # The output is a list containing ArtifactVersionResponse objects
            output_artifacts = pipeline_run.steps[
                "validate_batch_results"
            ].outputs["output"]

            if (
                isinstance(output_artifacts, list)
                and len(output_artifacts) > 0
            ):
                # Get the first artifact and load it
                results = output_artifacts[0].load()
                print(
                    f"Debug: Successfully loaded results type: {type(results)}"
                )
            else:
                raise ValueError("No output artifacts found")

        except Exception as e:
            print(f"⚠️  Could not extract results: {e}")
            results = {
                "validated_results": [],
                "summary_stats": {
                    "total_documents": len(file_paths),
                    "successful_extractions": 0,
                    "success_rate": 0.0,
                    "schema_compliance_rate": 0.0,
                },
            }

        print_results_summary(results)
        print_individual_results(results, args.show_details)

        if args.output:
            save_results_to_file(results, args.output)

        print("\n✅ Extraction complete!")

    except KeyboardInterrupt:
        print("\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
