"""Document analysis steps with LLM integration and fallback logic.

This module contains steps responsible for analyzing document content,
including LLM-based analysis with graceful fallbacks to deterministic
methods when LLM services are unavailable.
"""

import time
from collections import Counter
from typing import Annotated, Dict, List, Optional, cast

from models import AnalysisResponse, DocumentAnalysis, DocumentRequest
from steps.utils import (
    clean_text_content,
    extract_meaningful_summary,
    get_common_stop_words,
)

from zenml import step
from zenml.logger import get_logger

# Get ZenML logger for consistent logging
logger = get_logger(__name__)


def perform_llm_analysis(
    content: str,
    filename: str,
    model: str = "gpt-4o-mini",
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Perform document analysis using LLM services.

    Args:
        content: Document content to analyze
        filename: Document filename for context
        model: LLM model to use (default: gpt-4o-mini)
        metadata: Optional metadata for request tracking

    Returns:
        Dict containing analysis results with keys:
        - summary: Extracted summary text
        - keywords: List of relevant keywords
        - sentiment: Sentiment classification
        - readability_score: Readability score (0-1)
        - tokens_prompt: Number of prompt tokens used
        - tokens_completion: Number of completion tokens used
        - latency_ms: Processing time in milliseconds

    Raises:
        ImportError: If litellm is not available
    """
    logger.info(f"Starting LLM analysis for document: {filename}")

    try:
        # Lazy imports to avoid hard dependency when offline
        import instructor
        from litellm import completion

        # Clean content for better LLM analysis
        cleaned_content = clean_text_content(content)
        content_preview = cleaned_content[:2000]

        # Construct analysis prompt
        prompt = f"""Analyze this document and provide structured analysis.

Document: {filename}
Content: {content_preview}

Provide a concise summary, relevant keywords, sentiment analysis, and readability assessment."""

        logger.debug(
            f"Sending request to {model} with {len(prompt)} character prompt"
        )
        start_time = time.time()

        # Create instructor client with litellm
        client = instructor.from_litellm(completion)

        # Call LLM service with structured output
        response = client.chat.completions.create(
            model=model,
            response_model=AnalysisResponse,
            messages=[
                {
                    "role": "system",
                    "content": "You are a document analysis assistant. Provide structured analysis as requested.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            max_tokens=300,
            metadata=metadata or {},
        )

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Extract structured response
        analysis_response = response

        # Ensure we have 5 keywords
        keywords = analysis_response.keywords[
            :5
        ]  # Take first 5 if more provided
        while len(keywords) < 5:
            keywords.append(f"term{len(keywords) + 1}")

        # Convert readability to score
        readability_score_map = {"easy": 0.9, "medium": 0.6, "hard": 0.3}
        readability_score = readability_score_map.get(
            analysis_response.readability.lower(), 0.6
        )

        # For token counting, we'll estimate since instructor wraps the response
        tokens_prompt = len(prompt.split()) * 1.3  # Rough estimation
        tokens_completion = len(analysis_response.summary.split()) + len(
            " ".join(keywords).split()
        )

        logger.info(
            f"LLM analysis completed in {latency_ms}ms "
            f"(estimated tokens: {int(tokens_prompt)} prompt + {int(tokens_completion)} completion)"
        )

        logger.debug(
            f"LLM analysis results: {len(analysis_response.summary)} char summary, {len(keywords)} keywords"
        )

        return {
            "summary": analysis_response.summary,
            "keywords": keywords,
            "sentiment": analysis_response.sentiment,
            "readability_score": readability_score,
            "tokens_prompt": int(tokens_prompt),
            "tokens_completion": int(tokens_completion),
            "latency_ms": latency_ms,
        }

    except ImportError:
        logger.error("litellm package not available for LLM analysis")
        raise
    except Exception as e:
        logger.error(f"LLM analysis failed: {str(e)}")
        raise


def perform_deterministic_analysis(
    content: str, filename: str
) -> Dict[str, object]:
    """Simple fallback analysis when LLM is unavailable.

    Args:
        content: Document content to analyze
        filename: Document filename for context

    Returns:
        Dict containing analysis results with keys.
    """
    logger.info(f"Starting fallback analysis for document: {filename}")
    start_time = time.time()

    # Basic summary from first meaningful paragraph
    summary = extract_meaningful_summary(content, filename)

    # Simple keyword extraction
    words = clean_text_content(content).lower().split()
    common_words = get_common_stop_words()

    # Filter and count words
    filtered_words = [
        w
        for w in words
        if len(w) > 3 and w not in common_words and w.isalpha()
    ]
    word_freq = Counter(filtered_words)
    keywords = [word for word, _ in word_freq.most_common(5)]

    # Ensure 5 keywords
    while len(keywords) < 5:
        keywords.append(f"keyword{len(keywords) + 1}")

    # Simple sentiment (default to neutral)
    sentiment = "neutral"

    # Simple readability (based on average word length)
    avg_word_len = sum(len(w) for w in words) / len(words) if words else 5
    readability_score = max(
        0.1, 1.0 - (avg_word_len - 4) / 10
    )  # Rough heuristic

    latency_ms = int((time.time() - start_time) * 1000)

    return {
        "summary": summary,
        "keywords": keywords,
        "sentiment": sentiment,
        "readability_score": readability_score,
        "tokens_prompt": len(content.split()),
        "tokens_completion": len(summary.split()),
        "latency_ms": latency_ms,
    }


@step
def analyze_document_step(
    document: DocumentRequest,
) -> Annotated[DocumentAnalysis, "document_analysis"]:
    """Analyze document content using LLM or deterministic methods.

    This step performs comprehensive document analysis including summarization,
    keyword extraction, sentiment analysis, and readability assessment.
    It attempts to use LLM services first, with graceful fallback to
    deterministic methods when LLM services are unavailable.

    Args:
        document: Document request containing content and metadata

    Returns:
        DocumentAnalysis: Complete analysis results with metrics and metadata

    Raises:
        ValueError: If document content is invalid or empty

    Example:
        >>> document = DocumentRequest(filename="test.txt", content="Sample content")
        >>> analysis = analyze_document_step(document)
        >>> print(analysis.summary)
        'Sample content analysis summary...'
    """
    logger.info(f"Starting document analysis for: {document.filename}")

    # Validate input
    if not document.content or not document.content.strip():
        error_msg = f"Empty document content for file: {document.filename}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Attempt LLM analysis first, fall back to simple analysis if needed
    try:
        logger.info("Attempting LLM-based analysis")
        analysis_result = perform_llm_analysis(
            content=document.content,
            filename=document.filename,
            metadata={"source": "document_analysis_pipeline"},
        )
        analysis_method = "llm"
    except Exception as e:
        logger.warning(f"LLM analysis failed ({str(e)}), using fallback")
        analysis_result = perform_deterministic_analysis(
            content=document.content, filename=document.filename
        )
        analysis_method = "deterministic_fallback"

    # Create analysis object with results
    analysis = DocumentAnalysis(
        document=document,
        summary=cast(str, analysis_result["summary"]),
        keywords=cast(List[str], analysis_result["keywords"]),
        sentiment=cast(str, analysis_result["sentiment"]),
        word_count=len(document.content.split()),
        readability_score=float(
            cast(float, analysis_result["readability_score"])
        ),
        model=f"lite-llm-auto ({analysis_method})",
        latency_ms=int(cast(int, analysis_result["latency_ms"])),
        tokens_prompt=int(cast(int, analysis_result["tokens_prompt"])),
        tokens_completion=int(cast(int, analysis_result["tokens_completion"])),
        metadata={
            "source": "document_analysis_pipeline",
            "analysis_method": analysis_method,
            "document_type": document.document_type,
        },
    )

    logger.info(
        f"Document analysis completed: {analysis.word_count} words, "
        f"{analysis.latency_ms}ms, method={analysis_method}"
    )

    return analysis
