"""Data models for document analysis pipeline.

This module defines Pydantic models used throughout the document analysis
pipeline for request/response handling, analysis results, and evaluation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    """Structured response model for LLM analysis.

    Used with instructor to ensure structured JSON output from LLM calls
    instead of relying on regex parsing of text responses.
    """

    summary: str = Field(
        description="Concise 2-3 sentence summary focusing on main purpose/value"
    )
    keywords: List[str] = Field(
        description="5 key keywords or phrases, focus on meaningful terms"
    )
    sentiment: str = Field(
        description="Overall sentiment: positive, negative, or neutral"
    )
    readability: str = Field(
        description="Readability assessment: easy, medium, or hard"
    )


class DocumentRequest(BaseModel):
    """Model for document analysis requests.

    Represents a document that needs to be analyzed, including its content
    and metadata for processing through the analysis pipeline.

    Attributes:
        filename: Name of the document file
        content: Raw text content of the document
        document_type: Type classification (text, markdown, report, etc.)
        analysis_type: Depth of analysis to perform (full, summary_only, etc.)
        created_at: Timestamp when the request was created
    """

    filename: str
    content: str
    document_type: Optional[str] = Field(default="text")
    analysis_type: Optional[str] = Field(default="full")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class DocumentAnalysis(BaseModel):
    """Model for document analysis results.

    Contains the complete analysis output including summary, keywords,
    sentiment analysis, readability metrics, and processing metadata.

    Attributes:
        document: The original document request
        summary: Generated summary of the document
        keywords: List of extracted key terms
        sentiment: Detected sentiment (positive/negative/neutral)
        word_count: Total number of words in the document
        readability_score: Readability score (0-1, higher = more readable)
        model: Model/method used for analysis
        latency_ms: Processing time in milliseconds
        tokens_prompt: Number of input tokens used (for LLM analysis)
        tokens_completion: Number of output tokens used (for LLM analysis)
        metadata: Additional processing metadata
        created_at: Timestamp when the analysis was completed
    """

    document: DocumentRequest
    summary: str
    keywords: List[str]
    sentiment: str
    word_count: int
    readability_score: float
    model: str
    latency_ms: int
    tokens_prompt: int
    tokens_completion: int
    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AnalysisAnnotation(BaseModel):
    """Model for quality annotations of analysis results.

    Used in evaluation pipeline to assess the quality of document
    analysis outputs through manual or automated review.

    Attributes:
        summary_quality: Whether the summary accurately represents content
        keywords_relevant: Whether extracted keywords are relevant
        sentiment_accurate: Whether sentiment analysis is correct
        analysis_complete: Whether analysis covers all important aspects
        notes: Optional additional feedback or comments
    """

    # Quality assessment of the analysis
    summary_quality: bool
    keywords_relevant: bool
    sentiment_accurate: bool
    analysis_complete: bool
    notes: Optional[str] = None


class AnnotatedAnalysis(BaseModel):
    """Model combining analysis results with quality annotations.

    Links a document analysis with its quality assessment for
    evaluation and improvement of the analysis pipeline.

    Attributes:
        analysis: The document analysis results
        annotation: Quality assessment of the analysis
    """

    analysis: DocumentAnalysis
    annotation: AnalysisAnnotation


class EvaluationReport(BaseModel):
    """Model for analysis evaluation reports.

    Aggregates evaluation results across multiple analyzed documents
    to provide insights into pipeline performance and quality metrics.

    Attributes:
        total: Total number of analyses evaluated
        scores: Aggregated quality scores by metric type
        by_item: Individual analysis results with annotations
        html_report: Optional HTML-formatted evaluation report
    """

    total: int
    scores: Dict[str, float]
    by_item: List[AnnotatedAnalysis]
    html_report: Optional[str] = None
