"""ZenML pipeline for Pydantic AI EDA workflow.

This module contains the pipeline definition for the EDA workflow:

- eda_pipeline.py: Complete EDA pipeline with AI analysis and quality gates
"""

from .eda_pipeline import eda_pipeline

__all__ = [
    "eda_pipeline",
]