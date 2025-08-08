"""Document analysis steps with LLM integration and fallback logic.

This module contains steps responsible for analyzing document content,
including LLM-based analysis with graceful fallbacks to deterministic
methods when LLM services are unavailable.
"""

import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).parent.parent))

from models import DocumentAnalysis, DocumentRequest

from zenml import step
from zenml.logger import get_logger

from .utils import (
    clean_text_content,
    extract_field_from_llm_response,
    extract_meaningful_summary,
    get_common_stop_words,
    get_technical_filter_terms,
)

# Get ZenML logger for consistent logging
logger = get_logger(__name__)


def check_llm_availability() -> bool:
    """Check if LLM services are available via API keys.

    Returns:
        bool: True if any supported LLM provider API key is configured
    """
    supported_providers = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "COHERE_API_KEY",
    ]

    available = any(os.environ.get(var) for var in supported_providers)
    logger.info(
        f"LLM availability check: {'Available' if available else 'Not available'}"
    )
    return available


def perform_llm_analysis(
    content: str,
    filename: str,
    model: str = "gpt-3.5-turbo",
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Perform document analysis using LLM services.

    Args:
        content: Document content to analyze
        filename: Document filename for context
        model: LLM model to use (default: gpt-3.5-turbo)
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
        Exception: If LLM service call fails
    """
    logger.info(f"Starting LLM analysis for document: {filename}")

    try:
        # Lazy import to avoid hard dependency when offline
        from litellm import completion

        # Clean content for better LLM analysis
        cleaned_content = clean_text_content(content)
        content_preview = cleaned_content[:2000]

        # Construct analysis prompt
        prompt = f"""Analyze this document and provide:
1. A concise summary (2-3 sentences focusing on the main purpose/value)
2. 5 key keywords/phrases (comma-separated, focus on meaningful terms)
3. Overall sentiment (positive/negative/neutral)
4. Readability assessment (easy/medium/hard)

Document: {filename}
Content: {content_preview}

Format response as:
SUMMARY: [your summary]
KEYWORDS: [keyword1, keyword2, keyword3, keyword4, keyword5]
SENTIMENT: [positive/negative/neutral]  
READABILITY: [easy/medium/hard]"""

        messages = [
            {
                "role": "system",
                "content": "You are a document analysis assistant. Provide structured analysis as requested.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        logger.debug(
            f"Sending request to {model} with {len(prompt)} character prompt"
        )
        start_time = time.time()

        # Call LLM service
        response = completion(
            model=model,
            messages=messages,
            max_tokens=300,
            metadata=metadata or {},
        )

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Extract response content
        analysis_text = (
            response.choices[0].message["content"]
            if hasattr(response.choices[0], "message")
            else response.choices[0]["message"]["content"]
        )

        # Extract token usage
        tokens_prompt = int(
            getattr(response, "usage", {}).get("prompt_tokens", 0)
        )
        tokens_completion = int(
            getattr(response, "usage", {}).get("completion_tokens", 0)
        )

        logger.info(
            f"LLM analysis completed in {latency_ms}ms "
            f"(tokens: {tokens_prompt} prompt + {tokens_completion} completion)"
        )

        # Parse structured response
        summary = extract_field_from_llm_response(analysis_text, "SUMMARY")
        keywords_str = extract_field_from_llm_response(
            analysis_text, "KEYWORDS"
        )
        sentiment = extract_field_from_llm_response(analysis_text, "SENTIMENT")
        readability = extract_field_from_llm_response(
            analysis_text, "READABILITY"
        )

        # Process keywords
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
        if len(keywords) < 5:
            logger.warning(
                f"LLM returned only {len(keywords)} keywords, expected 5"
            )

        # Convert readability to score
        readability_score_map = {"easy": 0.9, "medium": 0.6, "hard": 0.3}
        readability_score = readability_score_map.get(readability.lower(), 0.6)

        logger.debug(
            f"LLM analysis results: {len(summary)} char summary, {len(keywords)} keywords"
        )

        return {
            "summary": summary,
            "keywords": keywords,
            "sentiment": sentiment,
            "readability_score": readability_score,
            "tokens_prompt": tokens_prompt,
            "tokens_completion": tokens_completion,
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
    """Perform document analysis using deterministic methods.

    Provides reliable analysis results without external dependencies,
    using rule-based approaches for content analysis.

    Args:
        content: Document content to analyze
        filename: Document filename for context

    Returns:
        Dict containing analysis results with same keys as LLM analysis
    """
    logger.info(f"Starting deterministic analysis for document: {filename}")
    start_time = time.time()

    # Clean content for analysis
    cleaned_content = clean_text_content(content)
    words = cleaned_content.lower().split()

    # Generate meaningful summary
    summary = extract_meaningful_summary(content, filename)

    # Extract keywords with intelligent filtering
    common_words = get_common_stop_words()
    technical_terms = get_technical_filter_terms()

    # Filter words intelligently
    filtered_words = []
    for word in words:
        if (
            len(word) > 3
            and word.isalpha()
            and word not in common_words
            and word not in technical_terms
            and not word.startswith("http")
            and word != "zenml"  # Filter out brand names
        ):
            filtered_words.append(word)

    # Extract top keywords by frequency
    word_freq = Counter(filtered_words)
    keywords = [word for word, _ in word_freq.most_common(5)]

    # Ensure we have 5 keywords
    while len(keywords) < 5:
        keywords.append(f"term{len(keywords) + 1}")

    # Perform sentiment analysis
    sentiment = analyze_sentiment_deterministic(words)

    # Calculate readability score
    readability_score = calculate_readability_score(cleaned_content, words)

    end_time = time.time()
    latency_ms = int((end_time - start_time) * 1000)

    logger.info(
        f"Deterministic analysis completed in {latency_ms}ms "
        f"(summary: {len(summary)} chars, keywords: {len(keywords)})"
    )

    return {
        "summary": summary,
        "keywords": keywords,
        "sentiment": sentiment,
        "readability_score": readability_score,
        "tokens_prompt": len(content.split()),
        "tokens_completion": len(summary.split()),
        "latency_ms": latency_ms,
    }


def analyze_sentiment_deterministic(words: List[str]) -> str:
    """Analyze sentiment using word-based rules.

    Args:
        words: List of words from cleaned document content

    Returns:
        str: Sentiment classification (positive/negative/neutral)
    """
    positive_words = {
        "good",
        "great",
        "excellent",
        "amazing",
        "wonderful",
        "positive",
        "success",
        "effective",
        "beneficial",
        "outstanding",
        "powerful",
        "unified",
        "comprehensive",
        "advanced",
        "robust",
        "reliable",
        "scalable",
        "flexible",
        "innovative",
        "helpful",
        "useful",
        "valuable",
        "impressive",
        "remarkable",
        "exceptional",
        "superior",
    }

    negative_words = {
        "bad",
        "terrible",
        "awful",
        "horrible",
        "negative",
        "failure",
        "problem",
        "poor",
        "disappointing",
        "inadequate",
        "struggle",
        "broken",
        "crack",
        "friction",
        "slow",
        "painful",
        "expensive",
        "complex",
        "difficult",
        "challenging",
        "limitation",
        "issue",
        "error",
        "bug",
        "fail",
        "wrong",
        "worst",
    }

    pos_count = sum(1 for word in words if word in positive_words)
    neg_count = sum(1 for word in words if word in negative_words)

    logger.debug(
        f"Sentiment analysis: {pos_count} positive, {neg_count} negative words"
    )

    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    else:
        return "neutral"


def calculate_readability_score(
    cleaned_content: str, words: List[str]
) -> float:
    """Calculate readability score based on text complexity metrics.

    Args:
        cleaned_content: Cleaned document text
        words: List of words from the content

    Returns:
        float: Readability score between 0 and 1 (higher = more readable)
    """
    if not words:
        return 0.5

    # Calculate basic metrics
    sentences = [s.strip() for s in cleaned_content.split(".") if s.strip()]
    sentence_count = len(sentences)

    avg_word_length = sum(len(word) for word in words) / len(words)
    avg_sentence_length = (
        len(words) / sentence_count if sentence_count > 0 else len(words)
    )

    # Adjust scoring for technical content
    complexity_factor = min(avg_word_length / 6, 1.0)
    length_factor = min(avg_sentence_length / 15, 1.0)

    # Calculate final score (higher = more readable)
    readability_score = max(0.1, 1.0 - (complexity_factor + length_factor) / 2)

    logger.debug(
        f"Readability metrics: avg_word_len={avg_word_length:.1f}, "
        f"avg_sent_len={avg_sentence_length:.1f}, score={readability_score:.2f}"
    )

    return readability_score


@step
def analyze_document_step(document: DocumentRequest) -> DocumentAnalysis:
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

    # Track analysis method used
    analysis_method = "unknown"

    try:
        # Attempt LLM analysis first
        if check_llm_availability():
            logger.info("Using LLM-based analysis")
            analysis_method = "llm"
            analysis_result = perform_llm_analysis(
                content=document.content,
                filename=document.filename,
                metadata={"source": "document_analysis_pipeline"},
            )
        else:
            logger.info("LLM not available, using deterministic analysis")
            analysis_method = "deterministic"
            analysis_result = perform_deterministic_analysis(
                content=document.content, filename=document.filename
            )

    except Exception as e:
        logger.warning(
            f"LLM analysis failed ({str(e)}), falling back to deterministic analysis"
        )
        analysis_method = "deterministic_fallback"
        analysis_result = perform_deterministic_analysis(
            content=document.content, filename=document.filename
        )

    # Create analysis object with results
    analysis = DocumentAnalysis(
        document=document,
        summary=str(analysis_result["summary"]),
        keywords=list(analysis_result["keywords"]),
        sentiment=str(analysis_result["sentiment"]),
        word_count=len(document.content.split()),
        readability_score=float(analysis_result["readability_score"]),
        model=f"lite-llm-auto ({analysis_method})",
        latency_ms=int(analysis_result["latency_ms"]),
        tokens_prompt=int(analysis_result["tokens_prompt"]),
        tokens_completion=int(analysis_result["tokens_completion"]),
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
