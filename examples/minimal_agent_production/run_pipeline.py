"""Standalone runner to execute the document analysis pipeline.

This is used by the FastAPI app to run the pipeline in a separate process,
avoiding signal handling constraints in non-main threads.
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

from pipelines.production import document_analysis_pipeline


def read_content(content: str | None, content_file: str | None) -> str:
    if content is not None:
        return content
    if content_file is not None:
        return Path(content_file).read_text(encoding="utf-8")
    raise ValueError("Either --content or --content_file must be provided")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", required=True)
    parser.add_argument("--content", required=False)
    parser.add_argument("--content_file", required=False)
    parser.add_argument("--document_type", required=True)
    parser.add_argument("--analysis_type", required=True)
    parser.add_argument("--output_json", required=False)
    args = parser.parse_args()

    try:
        content_value = read_content(args.content, args.content_file)
        # Redirect all stdout from the pipeline execution to stderr so that
        # this script's stdout remains clean JSON for the caller to parse.
        with redirect_stdout(sys.stderr):
            run = document_analysis_pipeline(
                filename=args.filename,
                content=content_value,
                document_type=args.document_type,
                analysis_type=args.analysis_type,
            )
        run_id = ""
        try:
            run_id = str(run.id)  # type: ignore[attr-defined]
        except Exception:
            run_id = ""

        # Try to extract the analysis result directly from the run's artifacts
        result_payload = None
        try:
            # Give the run a moment to fully complete and artifacts to be saved
            import time

            time.sleep(1)

            # Refresh the run to get latest state
            from zenml.client import Client

            client = Client()
            run = client.get_pipeline_run(run_id)

            step = None
            try:
                step = run.steps.get("analyze_document_step")
            except Exception:
                step = None
            # Try to find artifacts in a more systematic way
            artifacts_found = []

            # First try the analyze step specifically
            if step and hasattr(step, "outputs"):
                for output_name, output in step.outputs.items():
                    artifacts_found.append(output)

            # If no artifacts in analyze step, check all steps
            if not artifacts_found:
                for step_name, s in getattr(run, "steps", {}).items():
                    if hasattr(s, "outputs"):
                        for output_name, output in s.outputs.items():
                            artifacts_found.append(output)

            # Try to load each artifact
            for artifact_view in artifacts_found:
                try:
                    # Handle different artifact types
                    if hasattr(artifact_view, "load"):
                        analysis_result = artifact_view.load()
                    elif isinstance(artifact_view, list):
                        # If it's a list, try to access the first element
                        if len(artifact_view) > 0:
                            first_item = artifact_view[0]
                            if hasattr(first_item, "load"):
                                analysis_result = first_item.load()
                            else:
                                analysis_result = first_item
                        else:
                            continue
                    else:
                        analysis_result = artifact_view

                    # Check if it's a DocumentAnalysis object (or has the right attributes)
                    if hasattr(analysis_result, "summary") and hasattr(
                        analysis_result, "keywords"
                    ):
                        result_payload = {
                            "summary": str(analysis_result.summary),
                            "keywords": list(analysis_result.keywords),
                            "sentiment": str(analysis_result.sentiment),
                            "word_count": int(analysis_result.word_count),
                            "readability_score": float(
                                analysis_result.readability_score
                            ),
                        }
                        break
                except Exception:
                    continue
        except Exception:
            result_payload = None

        output = {"zenml_run_id": run_id, "result": result_payload}
        # Prefer writing to a file if provided to keep stdout clean
        if args.output_json:
            Path(args.output_json).write_text(
                json.dumps(output), encoding="utf-8"
            )
        else:
            print(json.dumps(output))
        return 0
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
