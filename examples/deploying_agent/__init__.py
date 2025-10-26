"""Document Analysis Pipeline - Production Ready with ZenML.

This example demonstrates how to build and deploy a document analysis system
as an HTTP endpoint using ZenML pipelines. Analyze documents with AI-powered
summarization, keyword extraction, sentiment analysis, and readability scoring.

Key Features:
- Deploy pipelines as scalable HTTP endpoints
- LLM-based analysis with deterministic fallbacks
- Quality evaluation and continuous improvement
- Web interface and programmatic client examples

Main Components:
- models.py: Pydantic data models
- pipelines/: Document analysis and evaluation pipelines
- steps/: Individual processing steps
- streamlit_app.py: Web interface
- run_evaluation.py: Quality assessment CLI
"""