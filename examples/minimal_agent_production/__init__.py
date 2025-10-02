"""Minimal Agent Production Example - Document Analysis Pipeline.

This example demonstrates a production-ready document analysis system using ZenML.
The system transforms documents through analysis pipelines instead of real-time
chat interfaces, making it ideal for batch processing workflows.

Key Features:
- Document upload and automatic type inference
- LLM-based analysis with deterministic fallbacks
- Quality evaluation and metrics collection
- HTML report generation for visualization
- Web interface for document submission

Main Components:
- models.py: Pydantic models for data validation
- pipelines/: ZenML pipeline definitions
- steps/: Individual pipeline step implementations
- app/: FastAPI web application
- run_production.py: Production pipeline execution
- run_evaluation.py: Quality evaluation pipeline
"""