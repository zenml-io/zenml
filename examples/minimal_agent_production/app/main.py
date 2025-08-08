"""FastAPI application for document analysis service.

This module provides a web interface for the document analysis pipeline,
including file upload capabilities, document processing, and HTML report
generation through a modern web interface.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import tempfile
import time

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pipelines.production import document_analysis_pipeline
from pydantic import BaseModel
from steps.utils import infer_document_type_from_content


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
    return infer_document_type_from_content(content)


def generate_filename(content: str) -> str:
    """Generate a filename based on document content."""
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


# Top-level function for multiprocessing (must be picklable)
def _run_pipeline_child(
    out_file: str,
    filename: str,
    content: str,
    document_type: str,
    analysis_type: str,
) -> None:
    from zenml.client import (
        Client as _Client,  # re-import inside child process
    )

    try:
        run = document_analysis_pipeline(
            filename=filename,
            content=content,
            document_type=document_type,
            analysis_type=analysis_type,
        )
        client_inner = _Client()
        timeout = 120
        waited_local = 0
        analysis_result = None
        run_id_str = ""
        while waited_local < timeout:
            try:
                fresh = client_inner.get_pipeline_run(run.id)
                run_id_str = str(fresh.id)

                # Check if the pipeline run is finished
                if fresh.status and hasattr(fresh.status, "value"):
                    if fresh.status.value in ("failed", "crashed"):
                        with open(out_file, "w") as f:
                            json.dump(
                                {
                                    "error": f"Pipeline failed: {fresh.status.value}",
                                    "run_id": run_id_str,
                                },
                                f,
                            )
                        return
                    elif fresh.status.value == "completed":
                        # Pipeline completed, wait a moment for artifacts to be available
                        time.sleep(2)

                        print(
                            f"Pipeline completed. Available steps: {list(fresh.steps.keys())}"
                        )

                        # Get the analysis result
                        step = fresh.steps.get("analyze_document_step")
                        if step:
                            print(
                                f"Found step, outputs type: {type(step.outputs)}"
                            )
                            print(f"Step outputs: {step.outputs}")

                            try:
                                # Try different ways to access the output
                                if hasattr(step, "output") and step.output:
                                    print("Trying step.output")
                                    analysis_result = step.output.load()
                                    print(
                                        f"Successfully loaded from step.output: {type(analysis_result)}"
                                    )
                                elif hasattr(step.outputs, "items"):
                                    print("Trying step.outputs.items()")
                                    for (
                                        output_name,
                                        output_artifact,
                                    ) in step.outputs.items():
                                        print(
                                            f"Trying to load output: {output_name}, type: {type(output_artifact)}"
                                        )
                                        analysis_result = (
                                            output_artifact.load()
                                        )
                                        print(
                                            f"Successfully loaded: {type(analysis_result)}"
                                        )
                                        break
                                elif isinstance(step.outputs, dict):
                                    print(
                                        "Outputs is dict, getting first value"
                                    )
                                    first_output = next(
                                        iter(step.outputs.values())
                                    )
                                    analysis_result = first_output.load()
                                    print(
                                        f"Successfully loaded from first output: {type(analysis_result)}"
                                    )
                                else:
                                    print(
                                        f"Unknown outputs structure: {type(step.outputs)}"
                                    )
                            except Exception as e:
                                print(f"Error loading step output: {e}")
                                continue
                        else:
                            print("No analyze_document_step found")

                        if analysis_result:
                            print("Breaking out of loop with analysis result")
                            break
                        else:
                            print(
                                "No analysis result found, continuing to wait"
                            )
                            # If still no result after pipeline completion, continue waiting
                            time.sleep(1)

            except Exception:
                # Log the error but continue trying
                pass
            time.sleep(1.0)
            waited_local += 1
        if analysis_result:
            try:
                result_data = {
                    "summary": analysis_result.summary,
                    "keywords": analysis_result.keywords,
                    "sentiment": analysis_result.sentiment,
                    "word_count": analysis_result.word_count,
                    "readability_score": analysis_result.readability_score,
                    "run_id": run_id_str,
                }
                with open(out_file, "w") as f:
                    json.dump(result_data, f)
            except Exception as e:
                with open(out_file, "w") as f:
                    json.dump(
                        {
                            "error": f"Failed to process analysis result: {str(e)}",
                            "run_id": run_id_str,
                        },
                        f,
                    )
        else:
            with open(out_file, "w") as f:
                json.dump(
                    {
                        "error": "Timeout waiting for analysis",
                        "run_id": run_id_str,
                    },
                    f,
                )
    except Exception as e:
        with open(out_file, "w") as f:
            json.dump({"error": str(e)}, f)


class DocumentRequest(BaseModel):
    """Request model for document analysis endpoints.

    Attributes:
        filename: Name of the document file
        content: Raw text content of the document
        document_type: Type classification of the document
        analysis_type: Depth of analysis to perform
    """

    filename: str = None
    content: str
    document_type: str = None
    analysis_type: str = "full"


app = FastAPI(title="Document Analysis Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Health check endpoint for service monitoring."""
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Return empty favicon response to prevent browser errors."""
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the main document analysis web interface."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Document Analysis Service</title>
      <style>
        body { 
          font-family: system-ui, Arial, sans-serif; 
          background: #f6f8fb; 
          margin: 0; 
          padding: 0; 
        }
        .container { 
          max-width: 900px; 
          margin: 0 auto; 
          padding: 24px; 
        }
        .header {
          text-align: center;
          margin-bottom: 30px;
        }
        h1 { 
          font-size: 28px; 
          margin: 0 0 8px; 
          color: #1e3a8a;
        }
        .subtitle {
          color: #6b7280;
          font-size: 16px;
        }
        .upload-area { 
          background: white; 
          border: 2px dashed #cbd5e1; 
          border-radius: 12px; 
          padding: 40px; 
          text-align: center; 
          margin-bottom: 20px;
          transition: all 0.3s;
          cursor: pointer;
        }
        .upload-area:hover {
          border-color: #2563eb;
          background: #fafbfc;
        }
        .upload-area.dragover {
          border-color: #2563eb;
          background: #f0f9ff;
          transform: scale(1.02);
        }
        textarea { 
          width: 100%; 
          height: 200px; 
          padding: 12px; 
          border: 1px solid #cbd5e1; 
          border-radius: 8px; 
          font-family: monospace;
          resize: vertical;
        }
        .form-row { 
          display: flex; 
          gap: 12px; 
          margin: 16px 0; 
        }
        .form-group {
          flex: 1;
        }
        label { 
          display: block; 
          margin-bottom: 4px; 
          font-weight: 500;
          color: #374151;
        }
        input[type=text], select { 
          width: 100%; 
          padding: 10px 12px; 
          border: 1px solid #cbd5e1; 
          border-radius: 6px; 
        }
        button { 
          padding: 12px 24px; 
          background: #2563eb; 
          color: white; 
          border: none; 
          border-radius: 8px; 
          cursor: pointer; 
          font-size: 16px;
          font-weight: 500;
          width: 100%;
        }
        button:disabled { 
          background: #94a3b8; 
          cursor: not-allowed; 
        }
        button:hover:not(:disabled) {
          background: #1d4ed8;
        }
        .results { 
          background: white; 
          border: 1px solid #e2e8f0; 
          border-radius: 12px; 
          padding: 20px; 
          margin-top: 20px; 
          display: none;
        }
        .results.show {
          display: block;
        }
        .result-section {
          margin-bottom: 20px;
        }
        .result-section h3 {
          margin: 0 0 8px;
          color: #1e3a8a;
        }
        .metrics {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
          margin: 12px 0;
        }
        .metric {
          background: #e3f2fd;
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 14px;
          font-weight: 500;
        }
        .keywords {
          background: #fff3e0;
          padding: 12px;
          border-radius: 6px;
          margin: 8px 0;
        }
        .summary {
          background: #f9f9f9;
          padding: 16px;
          border-left: 4px solid #2563eb;
          border-radius: 0 6px 6px 0;
        }
        .loading {
          text-align: center;
          padding: 40px;
          color: #6b7280;
        }
        .error {
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #dc2626;
          padding: 12px;
          border-radius: 6px;
          margin: 12px 0;
        }
        .file-info {
          background: #f0f9ff;
          border: 1px solid #dbeafe;
          padding: 16px;
          border-radius: 8px;
          margin: 16px 0;
        }
        .file-info p {
          margin: 4px 0;
          color: #1e40af;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>📄 Document Analysis Service</h1>
          <p class="subtitle">Upload text documents for AI-powered analysis including summarization, keyword extraction, and sentiment analysis</p>
        </div>
        
        <div class="upload-area" id="uploadArea">
          <p><strong>📤 Drop files here or click to select</strong></p>
          <p>Supported formats: TXT, MD, HTML, or paste text directly</p>
          <input type="file" id="fileInput" style="display: none;" accept=".txt,.md,.html,.csv,.json,.xml">
        </div>
        
        <div id="fileInfo" class="file-info" style="display: none;">
          <p><strong>📄 File:</strong> <span id="fileName"></span></p>
          <p><strong>📝 Type:</strong> <span id="fileType"></span> • <strong>📊 Size:</strong> <span id="fileSize"></span></p>
        </div>
        
        <form id="analysisForm">
          <label for="content">Document Content:</label>
          <textarea id="content" name="content" placeholder="Paste your document content here, or upload a file using the area above..." required></textarea>
          
          <button type="submit" id="analyzeBtn">🔍 Analyze Document</button>
        </form>
        
        <div id="results" class="results">
          <div class="loading" id="loadingState">
            <p>⏳ Analyzing document... This may take up to 2 minutes.</p>
          </div>
          <div id="analysisResults" style="display: none;">
            <div class="result-section">
              <h3>Summary</h3>
              <div class="summary" id="summaryText"></div>
            </div>
            
            <div class="result-section">
              <h3>Key Metrics</h3>
              <div class="metrics">
                <div class="metric">Words: <span id="wordCount"></span></div>
                <div class="metric">Sentiment: <span id="sentiment"></span></div>
                <div class="metric">Readability: <span id="readability"></span>/1.0</div>
              </div>
            </div>
            
            <div class="result-section">
              <h3>Keywords</h3>
              <div class="keywords" id="keywords"></div>
            </div>
          </div>
        </div>
      </div>
      
      <script>
        const form = document.getElementById('analysisForm');
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const contentTextarea = document.getElementById('content');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileType = document.getElementById('fileType');
        const fileSize = document.getElementById('fileSize');
        const results = document.getElementById('results');
        const loadingState = document.getElementById('loadingState');
        const analysisResults = document.getElementById('analysisResults');
        const analyzeBtn = document.getElementById('analyzeBtn');

        let currentFileData = null;

        // Click to upload
        uploadArea.addEventListener('click', () => {
          fileInput.click();
        });

        // File input change
        fileInput.addEventListener('change', handleFileSelect);

        function handleFileSelect(e) {
          const files = e.target.files;
          if (files.length > 0) {
            processFile(files[0]);
          }
        }

        // Drag and drop functionality
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
          uploadArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
          e.preventDefault();
          e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
          uploadArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
          uploadArea.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
          uploadArea.classList.add('dragover');
        }

        function unhighlight(e) {
          uploadArea.classList.remove('dragover');
        }

        uploadArea.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
          const dt = e.dataTransfer;
          const files = dt.files;
          
          if (files.length > 0) {
            processFile(files[0]);
          }
        }

        async function processFile(file) {
          try {
            const formData = new FormData();
            formData.append('file', file);
            
            showMessage('📤 Uploading file...', 'info');
            
            const response = await fetch('/upload', {
              method: 'POST',
              body: formData
            });
            
            if (!response.ok) {
              throw new Error(`Upload failed: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Update UI with file info
            fileName.textContent = data.filename;
            fileType.textContent = data.document_type.charAt(0).toUpperCase() + data.document_type.slice(1);
            fileSize.textContent = formatFileSize(data.size);
            fileInfo.style.display = 'block';
            
            // Set content
            contentTextarea.value = data.content;
            
            // Store file data for analysis
            currentFileData = {
              filename: data.filename,
              document_type: data.document_type,
              content: data.content
            };
            
            showMessage('✅ File uploaded successfully!', 'success');
            
          } catch (error) {
            showError('Upload failed: ' + error.message);
          }
        }

        function formatFileSize(bytes) {
          if (bytes === 0) return '0 Bytes';
          const k = 1024;
          const sizes = ['Bytes', 'KB', 'MB'];
          const i = Math.floor(Math.log(bytes) / Math.log(k));
          return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function showMessage(text, type) {
          const div = document.createElement('div');
          div.className = type === 'success' ? 'success' : type === 'info' ? 'info' : 'error';
          div.textContent = text;
          div.style.cssText = `
            padding: 12px; 
            border-radius: 6px; 
            margin: 12px 0;
            ${type === 'success' ? 'background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534;' : 
              type === 'info' ? 'background: #eff6ff; border: 1px solid #dbeafe; color: #1e40af;' : 
              'background: #fef2f2; border: 1px solid #fecaca; color: #dc2626;'}
          `;
          uploadArea.parentNode.insertBefore(div, uploadArea.nextSibling);
          setTimeout(() => div.remove(), 3000);
        }

        form.addEventListener('submit', async function(e) {
          e.preventDefault();
          
          const content = contentTextarea.value.trim();
          if (!content) {
            showError('Please provide document content');
            return;
          }
          
          const data = {
            content: content,
            filename: currentFileData?.filename,
            document_type: currentFileData?.document_type,
            analysis_type: 'full'
          };
          
          analyzeBtn.disabled = true;
          results.classList.add('show');
          loadingState.style.display = 'block';
          analysisResults.style.display = 'none';
          
          try {
            const response = await fetch('/analyze', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.error) {
              showError(result.error);
            } else {
              showResults(result);
            }
          } catch (error) {
            showError('Network error: ' + error.message);
          } finally {
            analyzeBtn.disabled = false;
            loadingState.style.display = 'none';
          }
        });

        function showResults(data) {
          document.getElementById('summaryText').textContent = data.summary;
          document.getElementById('wordCount').textContent = data.word_count;
          document.getElementById('sentiment').textContent = data.sentiment.charAt(0).toUpperCase() + data.sentiment.slice(1);
          document.getElementById('readability').textContent = data.readability_score.toFixed(2);
          document.getElementById('keywords').textContent = data.keywords.join(', ');
          
          analysisResults.style.display = 'block';
        }

        function showError(message) {
          const errorDiv = document.createElement('div');
          errorDiv.className = 'error';
          errorDiv.textContent = 'Error: ' + message;
          results.appendChild(errorDiv);
          setTimeout(() => errorDiv.remove(), 5000);
        }
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file and return its content with inferred metadata."""
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

        return {
            "filename": filename,
            "content": content,
            "document_type": document_type,
            "size": len(content),
            "lines": len(content.split("\n")),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing file: {str(e)}"
        )


@app.post("/analyze")
def analyze_document_endpoint(req: DocumentRequest):
    """Analyze a document using the ZenML pipeline.

    Args:
        req: Document request containing content and metadata

    Returns:
        JSON response with analysis results or error information
    """
    # Auto-infer filename and document type if not provided
    filename = req.filename or generate_filename(req.content)
    document_type = req.document_type or infer_document_type(
        filename, req.content
    )

    # Run the pipeline in a separate process to avoid signal handling in worker thread
    tmp_dir = tempfile.mkdtemp(prefix="doc_analysis_")
    out_file = os.path.join(tmp_dir, "analysis.json")
    proc = mp.Process(
        target=_run_pipeline_child,
        args=(
            out_file,
            filename,
            req.content,
            document_type,
            req.analysis_type,
        ),
    )
    proc.start()

    # Poll the output file up to timeout
    timeout_s = 130
    waited = 0
    while waited < timeout_s:
        if os.path.exists(out_file):
            try:
                with open(out_file, "r") as f:
                    data = json.load(f)
                if "summary" in data:
                    return JSONResponse(data)
                elif "error" in data:
                    return JSONResponse(
                        data,
                        status_code=500
                        if data["error"].lower().startswith("step failed")
                        else 202,
                    )
            except Exception:
                pass
        time.sleep(1.0)
        waited += 1

    return JSONResponse(
        {"error": "Timeout waiting for analysis"}, status_code=202
    )
