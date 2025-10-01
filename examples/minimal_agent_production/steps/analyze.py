"""Document analysis steps with LLM integration and fallback logic.

This module contains steps responsible for analyzing document content,
including LLM-based analysis with graceful fallbacks to deterministic
methods when LLM services are unavailable.
"""

import time
from collections import Counter
from typing import Annotated, Dict, List, Optional, cast

from constants import (
    CONTENT_PREVIEW_CHARS,
    DOC_ANALYSIS_LLM_MODEL,
    KEYWORD_COUNT,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    MODEL_LABEL_FMT,
    READABILITY_SCORE_MAP,
)
from models import (
    DocumentAnalysis,
    DocumentRequest,
)
from prompts import SYSTEM_PROMPT, build_analysis_prompt
from steps.utils import (
    clean_text_content,
    extract_meaningful_summary,
    get_common_stop_words,
)

from zenml import step


def perform_llm_analysis(
    content: str,
    filename: str,
    model: str = DOC_ANALYSIS_LLM_MODEL,
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Perform document analysis using OpenAI API.

    Args:
        content: Document content to analyze
        filename: Document filename for context
        model: OpenAI model to use (default: gpt-5-mini)
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
        ImportError: If openai is not available
    """
    try:
        # Lazy import to avoid hard dependency when offline
        import json

        from openai import OpenAI

        # Clean content for better LLM analysis and truncate preview
        cleaned_content = clean_text_content(content)
        content_preview = cleaned_content[:CONTENT_PREVIEW_CHARS]

        # Build analysis prompt
        prompt = build_analysis_prompt(
            filename=filename, content_preview=content_preview
        )

        start_time = time.time()

        # Create OpenAI client
        client = OpenAI()

        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,  # Low temperature for consistent output
        )

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Parse JSON response
        response_text = response.choices[0].message.content
        if response_text is None:
            response_text = ""
        try:
            analysis_response = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            analysis_response = {
                "summary": "Document analysis completed",
                "keywords": [
                    "document",
                    "analysis",
                    "text",
                    "content",
                    "review",
                ],
                "sentiment": "neutral",
                "readability": "medium",
            }

        # Ensure we have the desired number of keywords
        keywords = analysis_response.get("keywords", [])[:KEYWORD_COUNT]
        while len(keywords) < KEYWORD_COUNT:
            keywords.append(f"term{len(keywords) + 1}")

        # Convert readability to score via map
        readability_score = READABILITY_SCORE_MAP.get(
            analysis_response.get("readability", "medium").lower(),
            READABILITY_SCORE_MAP["medium"],
        )
        sentiment = analysis_response.get("sentiment", "neutral")

        # Get actual token usage from response
        tokens_prompt = (
            response.usage.prompt_tokens
            if response.usage
            else len(prompt.split()) * 1.3
        )
        tokens_completion = (
            response.usage.completion_tokens
            if response.usage
            else len(response_text.split())
            if response_text
            else 0
        )

        return {
            "summary": analysis_response.get(
                "summary", "Document analysis completed"
            ),
            "keywords": keywords,
            "sentiment": sentiment,
            "readability_score": readability_score,
            "tokens_prompt": int(tokens_prompt),
            "tokens_completion": int(tokens_completion),
            "latency_ms": latency_ms,
            "used_model": model,
        }

    except ImportError:
        raise
    except Exception:
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

    # Extract keywords and metrics
    keyword_count = KEYWORD_COUNT
    keywords = [word for word, _ in word_freq.most_common(keyword_count)]

    # Ensure we have the right number of keywords
    while len(keywords) < keyword_count:
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
    # Validate input
    if not document.content or not document.content.strip():
        raise ValueError(
            f"Empty document content for file: {document.filename}"
        )

    # Attempt LLM analysis first, fall back to simple analysis if needed
    try:
        analysis_result = perform_llm_analysis(
            content=document.content,
            filename=document.filename,
            metadata={"source": "document_analysis_pipeline"},
        )
        analysis_method = "llm"
    except Exception:
        analysis_result = perform_deterministic_analysis(
            content=document.content, filename=document.filename
        )
        analysis_method = "deterministic_fallback"

    # Determine appropriate model label based on analysis method
    if analysis_method == "llm":
        used_model = str(
            analysis_result.get("used_model", DOC_ANALYSIS_LLM_MODEL)
        )
        model_label = MODEL_LABEL_FMT.format(model=used_model)
    else:
        model_label = "rule-based (deterministic)"

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
        model=model_label,
        latency_ms=int(cast(int, analysis_result["latency_ms"])),
        tokens_prompt=int(cast(int, analysis_result["tokens_prompt"])),
        tokens_completion=int(cast(int, analysis_result["tokens_completion"])),
        metadata={
            "source": "document_analysis_pipeline",
            "analysis_method": analysis_method,
            "document_type": document.document_type,
        },
    )

    return analysis
