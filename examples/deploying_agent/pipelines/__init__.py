"""ZenML pipelines for document analysis.

This module contains the main document analysis pipeline for production use.
"""

from .doc_analyzer import doc_analyzer

__all__ = [
    "doc_analyzer",
]