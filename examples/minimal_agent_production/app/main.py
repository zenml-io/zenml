"""FastAPI application for document analysis service.

This module provides a web interface for the document analysis pipeline,
including file upload capabilities, document processing, and HTML report
generation through a modern web interface.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from steps.utils import infer_document_type_from_content

from zenml.logger import get_logger

# Get ZenML logger for consistent logging
logger = get_logger(__name__)


def infer_document_type(filename: str, content: str) -> str:
    """Infer document type based on filename extension and content.

    Args:
        filename: Document filename with extension
        content: Document text content

    Returns:
        str: Inferred document type
    """
    filename_lower = filename.lower()

    # Check file extension first
    extension_mappings = {
        (".md", ".markdown"): "markdown",
        (".txt", ".text"): "text",
        (".pdf",): "report",
        (".doc", ".docx"): "report",
        (".html", ".htm"): "article",
    }

    for extensions, doc_type in extension_mappings.items():
        if filename_lower.endswith(extensions):
            return doc_type

    # Fallback to content-based inference using utility function
    return str(infer_document_type_from_content(content))


def generate_filename(content: str) -> str:
    """Generate a filename based on document content.

    Args:
        content: Document text content to generate filename from

    Returns:
        str: Generated filename with .txt extension
    """
    lines = content.strip().split("\n")
    first_line = lines[0] if lines else "document"

    # Use first line as basis for filename, clean it up
    filename = first_line[:50].strip()

    # Remove problematic characters
    import re

    filename = re.sub(r"[^\w\s-]", "", filename)
    filename = re.sub(r"\s+", "_", filename)

    # Ensure it's not empty
    if not filename:
        filename = "document"

    return f"{filename}.txt"


# Global storage for analysis results (in production, use Redis or a database)
ANALYSIS_RESULTS = {}


app = FastAPI(title="Document Analysis Service")

# CORS middleware - configured for development only.
# In production, restrict origins to specific domains for security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint for service monitoring.

    Returns:
        dict[str, str]: Health status response
    """
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Return empty favicon response to prevent browser errors.

    Returns:
        Response: Empty 204 No Content response
    """
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the main document analysis web interface.

    Returns:
        HTMLResponse: Complete HTML page for document analysis UI

    Raises:
        HTTPException: If template file is not found
    """
    # Read template files (use absolute paths from the app directory)
    import os

    base_path = os.path.dirname(
        os.path.dirname(__file__)
    )  # Go up to examples/minimal_agent_production
    template_path = os.path.join(
        base_path, "static", "templates", "index.html"
    )
    css_path = os.path.join(base_path, "static", "css", "main.css")
    js_path = os.path.join(base_path, "static", "js", "main.js")

    logger.info(f"Loading template from: {template_path}")
    logger.info(f"Loading CSS from: {css_path}")
    logger.info(f"Loading JS from: {js_path}")

    try:
        with open(template_path, "r") as f:
            html_content = f.read()
    except FileNotFoundError:
        logger.error(f"Template file not found at {template_path}")
        raise HTTPException(status_code=500, detail="Template file not found")

    try:
        with open(css_path, "r") as f:
            css_content = f.read()
    except FileNotFoundError:
        logger.warning(
            f"CSS file not found at {css_path}, using fallback styles"
        )
        css_content = "/* Fallback styles */ body { font-family: Arial, sans-serif; margin: 20px; }"

    try:
        with open(js_path, "r") as f:
            js_content = f.read()
    except FileNotFoundError:
        logger.warning(
            f"JavaScript file not found at {js_path}, using fallback"
        )
        js_content = "console.log('JavaScript file not found');"

    # Replace placeholders in template
    html_content = html_content.replace("{CSS_CONTENT}", css_content)
    html_content = html_content.replace("{JAVASCRIPT_CONTENT}", js_content)

    return HTMLResponse(content=html_content)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """Upload a file and return its content with inferred metadata.

    Args:
        file: The uploaded file to process

    Returns:
        JSONResponse: File metadata including filename, content, type, and size

    Raises:
        HTTPException: If file processing fails or file is not text-based
    """
    try:
        # Read file content
        content_bytes = await file.read()

        # Try to decode as text
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = content_bytes.decode("latin-1")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="File must be text-based (UTF-8 or Latin-1 encoding)",
                )

        # Infer document type and generate clean filename
        filename = file.filename or generate_filename(content)
        document_type = infer_document_type(filename, content)

        return JSONResponse(
            {
                "filename": filename,
                "content": content,
                "document_type": document_type,
                "size": len(content),
                "lines": len(content.split("\n")),
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing file: {str(e)}"
        )


class AnalyzeRequest(BaseModel):
    """Request model for document analysis endpoint."""

    filename: str | None = None
    content: str
    document_type: str | None = None
    analysis_type: str = "full"


@app.post("/analyze")
def analyze_document_endpoint(req: AnalyzeRequest) -> JSONResponse:
    """Start document analysis and return a task ID for polling.

    Args:
        req: Document request containing content and metadata

    Returns:
        JSON response with task ID for polling results

    Raises:
        RuntimeError: If pipeline fails to start
    """
    # Auto-infer filename and document type if not provided
    filename = req.filename or generate_filename(req.content)
    document_type = req.document_type or infer_document_type(
        filename, req.content
    )

    # Generate unique run ID
    run_id = str(uuid.uuid4())

    # Initialize status
    ANALYSIS_RESULTS[run_id] = {"status": "running"}

    # Run pipeline directly - frontend will poll for results
    try:
        # Run the pipeline directly with JSON-serializable primitives
        logger.info(f"Starting pipeline run {run_id} for document: {filename}")
        # Run pipeline in a separate process to avoid signal issues in non-main thread
        import json
        import os
        import subprocess
        import sys
        import tempfile

        base_path = os.path.dirname(os.path.dirname(__file__))
        runner = os.path.join(base_path, "run_pipeline.py")
        # For very large content, write to a temp file to avoid argv limits
        temp_path = None
        output_json_path = None
        try:
            cmd = [
                sys.executable,
                runner,
                "--filename",
                filename,
                "--document_type",
                document_type,
                "--analysis_type",
                req.analysis_type,
            ]
            # Create a temp output path to get clean JSON without parsing stdout
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, encoding="utf-8", suffix=".json"
            ) as of:
                output_json_path = of.name
            cmd.extend(["--output_json", output_json_path])
            if len(req.content) > 20000:
                with tempfile.NamedTemporaryFile(
                    mode="w", delete=False, encoding="utf-8", suffix=".txt"
                ) as tf:
                    tf.write(req.content)
                    temp_path = tf.name
                cmd.extend(["--content_file", temp_path])
            else:
                cmd.extend(["--content", req.content])

            proc = subprocess.run(cmd, capture_output=True, text=True)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            # We do not remove output_json_path yet; we need to read it first
        try:
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or "Runner failed")
            if not output_json_path or not os.path.exists(output_json_path):
                raise RuntimeError("Runner did not produce output JSON")
            payload_text = (
                open(output_json_path, "r", encoding="utf-8").read().strip()
            )
            payload = json.loads(payload_text or "{}")
        except json.JSONDecodeError:
            payload = {
                "error": proc.stderr.strip() or "Invalid JSON from runner"
            }
        finally:
            if output_json_path and os.path.exists(output_json_path):
                try:
                    os.remove(output_json_path)
                except OSError:
                    pass

        if proc.returncode != 0 or "error" in payload:
            raise RuntimeError(
                payload.get("error") or "Pipeline runner failed"
            )

        # If result payload already available (e.g., cached run), return immediately
        result_payload = (
            payload.get("result") if isinstance(payload, dict) else None
        )
        if result_payload and all(
            key in result_payload
            for key in [
                "summary",
                "keywords",
                "sentiment",
                "word_count",
                "readability_score",
            ]
        ):
            ANALYSIS_RESULTS[run_id] = {
                "status": "completed",
                **result_payload,
            }
        else:
            ANALYSIS_RESULTS[run_id] = {
                "status": "running",
                "zenml_run_id": payload.get("zenml_run_id", ""),
            }

    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}")
        ANALYSIS_RESULTS[run_id] = {
            "status": "error",
            "error": f"Failed to start pipeline: {str(e)}",
        }

    return JSONResponse(
        {
            "run_id": run_id,
            "status": "started",
            "message": "Analysis started. Use GET /result/{run_id} to check status.",
        }
    )


@app.get("/result/{run_id}")
def get_analysis_result(run_id: str) -> JSONResponse:
    """Get analysis results by run ID.

    Args:
        run_id: Unique identifier for the analysis run

    Returns:
        JSON response with analysis results or status

    Raises:
        HTTPException: If analysis run is not found
    """
    if run_id not in ANALYSIS_RESULTS:
        raise HTTPException(status_code=404, detail="Analysis run not found")

    result = ANALYSIS_RESULTS[run_id]

    # If already completed or errored, return immediately
    if result["status"] in ["completed", "error"]:
        if result["status"] == "error":
            return JSONResponse(
                {"status": "error", "error": result["error"]}, status_code=500
            )
        else:
            # Clean up completed result after returning
            completed_result = ANALYSIS_RESULTS.pop(run_id)
            return JSONResponse(completed_result)

    # Check ZenML run status
    if "zenml_run_id" in result:
        try:
            from zenml.client import Client

            client = Client()
            zenml_run = client.get_pipeline_run(result["zenml_run_id"])

            # Normalize status across ZenML versions
            status_value = (
                getattr(zenml_run.status, "value", None)
                if getattr(zenml_run, "status", None) is not None
                else None
            )
            if status_value is None:
                status_value = str(getattr(zenml_run, "status", "")).lower()

            if status_value in ("failed", "crashed"):
                ANALYSIS_RESULTS[run_id] = {
                    "status": "error",
                    "error": f"Pipeline failed: {status_value}",
                }
                return JSONResponse(
                    {
                        "status": "error",
                        "error": f"Pipeline failed: {status_value}",
                    },
                    status_code=500,
                )
            elif status_value == "completed":
                # Simple direct access to the known artifact
                try:
                    analyze_step = zenml_run.steps["analyze_document_step"]
                    document_analysis_artifacts = analyze_step.outputs[
                        "document_analysis"
                    ]

                    if (
                        document_analysis_artifacts
                        and len(document_analysis_artifacts) > 0
                    ):
                        analysis_result = document_analysis_artifacts[0].load()

                        completed_data = {
                            "status": "completed",
                            "summary": analysis_result.summary,
                            "keywords": analysis_result.keywords,
                            "sentiment": analysis_result.sentiment,
                            "word_count": analysis_result.word_count,
                            "readability_score": analysis_result.readability_score,
                        }
                        ANALYSIS_RESULTS.pop(run_id)  # Clean up
                        return JSONResponse(completed_data)
                except Exception:
                    pass

                ANALYSIS_RESULTS[run_id] = {
                    "status": "error",
                    "error": "No analysis results found in pipeline output",
                }
                return JSONResponse(
                    {"status": "error", "error": "No analysis results found"},
                    status_code=500,
                )
        except Exception as e:
            logger.warning(f"Error checking pipeline status: {e}")

    # Still running
    return JSONResponse(
        {"status": "running", "message": "Analysis in progress..."},
        status_code=202,
    )
