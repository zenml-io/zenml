"""LLM utilities for document analysis with fallback support.

This module provides utilities for document analysis using LLM services
with graceful fallback to deterministic analysis when LLM services are
unavailable. It supports multiple LLM providers via LiteLLM.
"""

from __future__ import annotations

import os
import re
import time
from collections import Counter
from typing import Dict, Optional


def use_real_llm() -> bool:
    """Check if LLM services are available via environment variables.

    Returns:
        bool: True if any supported LLM provider API key is configured
    """
    # LiteLLM supports many providers. We check common envs to decide.
    return any(
        os.environ.get(var)
        for var in [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GROQ_API_KEY",
            "COHERE_API_KEY",
        ]
    )


def analyze_document_with_fallback(
    content: str,
    filename: str,
    model: str = "gpt-3.5-turbo",
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Analyze a document using LLM with deterministic fallback.

    Args:
        content: Raw document content to analyze
        filename: Name of the document (for context)
        model: LLM model identifier to use when available
        metadata: Optional request metadata to pass to the LLM client

    Returns:
        Dict with keys: summary (str), keywords (list[str]), sentiment (str),
        readability_score (float), tokens_prompt (int), tokens_completion (int),
        latency_ms (int)
    """
    start = time.time()
    if use_real_llm():
        try:
            # Lazy import to avoid hard dependency when offline
            from litellm import completion

            # Clean content for LLM analysis
            cleaned_for_llm = clean_text_content(content)

            prompt = f"""Analyze this document and provide:
1. A concise summary (2-3 sentences focusing on the main purpose/value)
2. 5 key keywords/phrases (comma-separated, focus on meaningful terms)
3. Overall sentiment (positive/negative/neutral)
4. Readability assessment (easy/medium/hard)

Document: {filename}
Content: {cleaned_for_llm[:2000]}

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
            response = completion(
                model=model,
                messages=messages,
                max_tokens=300,
                metadata=metadata or {},
            )
            analysis_text = (
                response.choices[0].message["content"]
                if hasattr(response.choices[0], "message")
                else response.choices[0]["message"]["content"]
            )
            tokens_prompt = int(
                getattr(response, "usage", {}).get("prompt_tokens", 0)
            )
            tokens_completion = int(
                getattr(response, "usage", {}).get("completion_tokens", 0)
            )

            # Parse LLM response
            summary = extract_field(analysis_text, "SUMMARY")
            keywords_str = extract_field(analysis_text, "KEYWORDS")
            sentiment = extract_field(analysis_text, "SENTIMENT")
            readability = extract_field(analysis_text, "READABILITY")

            keywords = [
                k.strip() for k in keywords_str.split(",") if k.strip()
            ]
            readability_score = {"easy": 0.9, "medium": 0.6, "hard": 0.3}.get(
                readability.lower(), 0.6
            )

        except Exception:
            # Graceful fallback
            analysis = deterministic_analysis(content, filename)
            summary = str(analysis["summary"])
            keywords = list(analysis["keywords"])  # type: ignore
            sentiment = str(analysis["sentiment"])
            readability_score = float(
                str(analysis.get("readability_score", 0.5))
            )
            tokens_prompt = len(content.split())
            tokens_completion = len(summary.split())
    else:
        analysis = deterministic_analysis(content, filename)
        summary = str(analysis["summary"])
        keywords = list(analysis["keywords"])  # type: ignore
        sentiment = str(analysis["sentiment"])
        readability_score = float(str(analysis.get("readability_score", 0.5)))
        tokens_prompt = len(content.split())
        tokens_completion = len(summary.split())

    latency_ms = int((time.time() - start) * 1000)
    return {
        "summary": summary,
        "keywords": keywords,
        "sentiment": sentiment,
        "readability_score": readability_score,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "latency_ms": latency_ms,
    }


def clean_text_content(content: str) -> str:
    """Clean markdown and HTML content for better analysis.

    Args:
        content: Raw text content that may include markdown/HTML

    Returns:
        Cleaned plain-text string suitable for analysis
    """
    import re

    # Remove HTML tags
    content = re.sub(r"<[^>]+>", "", content)

    # Remove markdown image syntax
    content = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", content)

    # Remove markdown reference-style links completely
    content = re.sub(r"\[[^\]]+\]\[[^\]]+\]", "", content)

    # Remove markdown link references at bottom
    content = re.sub(
        r"^\[[^\]]+\]:\s*https?://[^\s]+.*$", "", content, flags=re.MULTILINE
    )

    # Remove markdown links but keep the text
    content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)

    # Remove markdown headers (keep the text)
    content = re.sub(r"^#{1,6}\s*", "", content, flags=re.MULTILINE)

    # Remove markdown bold/italic
    content = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", content)
    content = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", content)

    # Remove code blocks
    content = re.sub(r"```[^`]*```", "", content, flags=re.DOTALL)
    content = re.sub(r"`([^`]+)`", r"\1", content)

    # Remove markdown horizontal rules
    content = re.sub(r"^-{3,}$", "", content, flags=re.MULTILINE)
    content = re.sub(r"^={3,}$", "", content, flags=re.MULTILINE)

    # Remove badge/shield markdown syntax
    content = re.sub(r"!\[[^\]]*\]\[[^\]]*\]", "", content)
    content = re.sub(r"\[[^\]]*-shield\]", "", content)
    content = re.sub(r"\[[^\]]*-url\]", "", content)

    # Remove comment syntax
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

    # Remove URLs
    content = re.sub(r"https?://[^\s]+", "", content)

    # Remove email addresses
    content = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "", content
    )

    # Remove markdown list indicators
    content = re.sub(r"^\s*[-*+]\s*", "", content, flags=re.MULTILINE)

    # Remove emoji at start of lines (common in README files)
    content = re.sub(
        r"^[🚨💡📚🖼️📖🏢🎓🤝❓📜🛠]\s*", "", content, flags=re.MULTILINE
    )

    # Clean up extra whitespace
    content = re.sub(r"\n+", "\n", content)
    content = re.sub(r"\s+", " ", content)

    return content.strip()


def extract_meaningful_summary(content: str, filename: str) -> str:
    """Extract a meaningful summary from document content.

    Args:
        content: Raw document content
        filename: Document name used in fallback summary

    Returns:
        Concise summary string (2-3 sentences when possible)
    """
    cleaned_content = clean_text_content(content)

    # Split into paragraphs and sentences
    paragraphs = [p.strip() for p in cleaned_content.split("\n") if p.strip()]

    # Find the first substantial paragraph (more than just a title)
    meaningful_text = ""
    for para in paragraphs:
        if len(para) > 50:  # Skip very short lines (likely headers)
            meaningful_text = para
            break

    if meaningful_text:
        # Extract first 2-3 sentences from the meaningful content
        sentences = re.split(r"[.!?]+", meaningful_text)
        summary_sentences = []
        total_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and total_length < 200:
                summary_sentences.append(sentence)
                total_length += len(sentence)
            if len(summary_sentences) >= 3:
                break

        if summary_sentences:
            summary = ". ".join(summary_sentences)
            if not summary.endswith("."):
                summary += "."
            return summary

    # Fallback: try to extract from document structure
    lines = cleaned_content.split("\n")
    non_empty_lines = [line.strip() for line in lines if line.strip()]

    if non_empty_lines:
        # Look for description-like content
        for line in non_empty_lines:
            if len(line) > 100 and not line.isupper():
                return line[:200] + ("..." if len(line) > 200 else "")

    return f"This document appears to be a {infer_document_type_from_content(content)} containing {len(content.split())} words."


def infer_document_type_from_content(content: str) -> str:
    """Infer document type from content patterns.

    Args:
        content: Raw document content

    Returns:
        Inferred document type label
    """
    content_lower = content.lower()

    if "readme" in content_lower or "installation" in content_lower:
        return "documentation"
    elif "import" in content_lower and "python" in content_lower:
        return "technical guide"
    elif "mlops" in content_lower or "machine learning" in content_lower:
        return "ML documentation"
    else:
        return "document"


def deterministic_analysis(content: str, filename: str) -> Dict[str, object]:
    """Deterministic document analysis using simple rules.

    Args:
        content: Raw document content to analyze
        filename: Name of the document (for context)

    Returns:
        Dict with summary, keywords, sentiment, readability_score
    """
    # Clean content for analysis
    cleaned_content = clean_text_content(content)
    words = cleaned_content.lower().split()

    # Generate meaningful summary
    summary = extract_meaningful_summary(content, filename)

    # Extract keywords with better filtering
    common_words = {
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "been",
        "have",
        "has",
        "had",
        "will",
        "would",
        "could",
        "should",
        "this",
        "that",
        "these",
        "those",
        "a",
        "an",
        "you",
        "your",
        "can",
        "get",
        "use",
        "using",
        "used",
        "make",
        "more",
        "most",
        "about",
        "into",
        "from",
        "here",
        "how",
        "what",
        "when",
        "where",
        "who",
        "why",
        "all",
        "any",
        "both",
        "each",
        "few",
        "may",
        "must",
        "our",
        "out",
        "own",
        "same",
        "such",
        "than",
        "too",
        "very",
        "will",
        "work",
        "first",
        "also",
        "after",
        "back",
        "other",
        "many",
        "them",
        "well",
        "were",
    }

    # Filter words more intelligently
    filtered_words = []
    for word in words:
        if (
            len(word) > 3
            and word.isalpha()
            and word not in common_words
            and not word.startswith("http")
            and word != "zenml"
        ):  # Exclude brand names that appear frequently
            filtered_words.append(word)

    word_freq = Counter(filtered_words)
    keywords = [word for word, _ in word_freq.most_common(8)]

    # Filter keywords to remove technical artifacts
    technical_terms = {
        "docs",
        "book",
        "gitbook",
        "assets",
        "href",
        "img",
        "src",
        "alt",
        "div",
        "align",
    }
    keywords = [k for k in keywords if k not in technical_terms][:5]

    # Ensure we have 5 keywords
    while len(keywords) < 5:
        keywords.append(f"term{len(keywords) + 1}")

    # Enhanced sentiment analysis
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
    }

    pos_count = sum(1 for word in words if word in positive_words)
    neg_count = sum(1 for word in words if word in negative_words)

    # Weight sentiment based on document context
    if pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    # Improved readability calculation
    sentences = re.split(r"[.!?]+", cleaned_content)
    sentence_count = len([s for s in sentences if s.strip()])

    if words:
        avg_word_length = sum(len(word) for word in words) / len(words)
        avg_sentence_length = (
            len(words) / sentence_count if sentence_count > 0 else len(words)
        )

        # More sophisticated readability scoring
        complexity_factor = min(
            avg_word_length / 6, 1.0
        )  # Adjusted for technical content
        length_factor = min(
            avg_sentence_length / 15, 1.0
        )  # Adjusted for technical content
        readability_score = max(
            0.1, 1.0 - (complexity_factor + length_factor) / 2
        )
    else:
        readability_score = 0.5

    return {
        "summary": summary,
        "keywords": keywords,
        "sentiment": sentiment,
        "readability_score": readability_score,
    }


def extract_field(text: str, field_name: str) -> str:
    """Extract a field from structured LLM response.

    Args:
        text: Text blob returned by the LLM
        field_name: Field name to extract (e.g., "SUMMARY")

    Returns:
        Extracted value or "N/A" if not found
    """
    pattern = f"{field_name}:\\s*(.+?)(?=\\n[A-Z]+:|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else "N/A"
