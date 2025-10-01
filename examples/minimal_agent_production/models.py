"""Data models for document analysis pipeline.

This module defines Pydantic models used throughout the document analysis
pipeline for request/response handling, analysis results, and evaluation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# Type definitions for constrained string values
SentimentType = Literal["positive", "negative", "neutral"]
ReadabilityType = Literal["easy", "medium", "hard"]


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
    sentiment: SentimentType = Field(
        description="Overall sentiment: positive, negative, or neutral"
    )
    readability: ReadabilityType = Field(
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
        created_at: Timestamp when the request was created
    """

    filename: str
    content: str
    document_type: Optional[str] = Field(default="text")
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
    sentiment: SentimentType
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
