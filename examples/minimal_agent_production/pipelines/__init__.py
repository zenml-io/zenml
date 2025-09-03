"""ZenML pipelines for document analysis.

This module contains pipeline definitions for document analysis workflows:

- production.py: Main document analysis pipeline
- evaluation.py: Quality evaluation and assessment pipeline  
"""

from .evaluation import evaluation_pipeline
from .production import document_analysis_pipeline

__all__ = [
    "document_analysis_pipeline",
    "evaluation_pipeline",
]