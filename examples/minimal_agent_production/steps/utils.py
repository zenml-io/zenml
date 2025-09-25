"""Utility functions for document text processing and analysis.

This module provides text processing utilities used across the document
analysis pipeline, including markdown/HTML cleaning, content extraction,
and document type inference.
"""

import re
from typing import Optional

from zenml.logger import get_logger

# Get ZenML logger for consistent logging
logger = get_logger(__name__)


def clean_text_content(content: str) -> str:
    """Clean markdown and HTML content for better analysis.

    Removes various markup elements while preserving meaningful text content.
    This function is essential for accurate text analysis of documents that
    contain markup syntax.

    Args:
        content: Raw text content that may contain HTML/markdown

    Returns:
        str: Cleaned text content with markup removed

    Example:
        >>> content = "# Title\\n**Bold text** with [link](url)"
        >>> clean_text_content(content)
        'Title Bold text with link'
    """
    logger.debug("Cleaning text content for analysis")

    if not content:
        logger.warning("Empty content provided to clean_text_content")
        return ""

    original_length = len(content)

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

    # Remove badge/shield markdown syntax (common in README files)
    content = re.sub(r"!\[[^\]]*\]\[[^\]]*\]", "", content)
    content = re.sub(r"\[[^\]]*-shield\]", "", content)
    content = re.sub(r"\[[^\]]*-url\]", "", content)

    # Remove HTML/markdown comments
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

    # Remove URLs and email addresses
    content = re.sub(r"https?://[^\s]+", "", content)
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

    cleaned_content = content.strip()
    cleaned_length = len(cleaned_content)

    logger.debug(
        f"Text cleaning completed: {original_length} -> {cleaned_length} chars "
        f"({((original_length - cleaned_length) / original_length * 100):.1f}% removed)"
    )

    return cleaned_content


def extract_meaningful_summary(
    content: str, filename: Optional[str] = None
) -> str:
    """Extract a meaningful summary from document content.

    Intelligently extracts the most relevant content from a document to create
    a concise summary. Uses document structure analysis to find substantive
    paragraphs while avoiding headers and metadata.

    Args:
        content: Document text content
        filename: Optional filename for context in fallback summaries

    Returns:
        str: Extracted summary text (2-3 sentences, max ~200 chars)

    Example:
        >>> content = "# Title\\n\\nThis is the main content..."
        >>> extract_meaningful_summary(content)
        'This is the main content...'
    """
    logger.debug(f"Extracting summary for document: {filename or 'unknown'}")

    if not content:
        logger.warning("Empty content provided for summary extraction")
        return "No content available for analysis."

    # Clean content first for better analysis
    cleaned_content = clean_text_content(content)

    # Split into paragraphs and find substantial content
    paragraphs = [p.strip() for p in cleaned_content.split("\n") if p.strip()]

    meaningful_text = ""
    for para in paragraphs:
        # Skip very short lines (likely headers or metadata)
        if len(para) > 50:
            meaningful_text = para
            logger.debug(
                f"Found meaningful paragraph with {len(para)} characters"
            )
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

            logger.debug(f"Generated summary with {len(summary)} characters")
            return summary

    # Fallback: try to extract from document structure
    lines = cleaned_content.split("\n")
    non_empty_lines = [line.strip() for line in lines if line.strip()]

    if non_empty_lines:
        # Look for description-like content
        for line in non_empty_lines:
            if len(line) > 100 and not line.isupper():
                summary = line[:200] + ("..." if len(line) > 200 else "")
                logger.debug("Using fallback line-based summary")
                return summary

    # Final fallback
    doc_type = infer_document_type_from_content(content)
    word_count = len(content.split())
    fallback_summary = f"This document appears to be a {doc_type} containing {word_count} words."

    logger.debug("Using final fallback summary")
    return fallback_summary


def infer_document_type_from_content(content: str) -> str:
    """Infer document type from content patterns.

    Analyzes text content to determine the likely document type based on
    common patterns and keywords found in different document categories.

    Args:
        content: Document text content to analyze

    Returns:
        str: Inferred document type (documentation, technical guide, etc.)

    Example:
        >>> content = "# Installation Guide\\npip install package"
        >>> infer_document_type_from_content(content)
        'documentation'
    """
    if not content:
        return "document"

    content_lower = content.lower()

    # Define patterns for different document types
    doc_patterns = {
        "documentation": [
            "readme",
            "installation",
            "getting started",
            "setup",
            "guide",
        ],
        "technical guide": [
            "import",
            "python",
            "class",
            "function",
            "def ",
            "```python",
        ],
        "ML documentation": [
            "mlops",
            "machine learning",
            "model",
            "training",
            "pipeline",
        ],
        "report": [
            "executive summary",
            "conclusion",
            "findings",
            "methodology",
            "analysis",
        ],
        "article": [
            "author:",
            "published:",
            "abstract:",
            "introduction",
            "journal",
        ],
    }

    # Score each document type based on pattern matches
    type_scores = {}
    for doc_type, patterns in doc_patterns.items():
        score = sum(1 for pattern in patterns if pattern in content_lower)
        if score > 0:
            type_scores[doc_type] = score

    if type_scores:
        # Return the type with the highest score
        best_type = max(type_scores, key=lambda k: type_scores[k])
        logger.debug(
            f"Inferred document type: {best_type} (score: {type_scores[best_type]})"
        )
        return best_type

    logger.debug("Could not infer specific document type, using 'document'")
    return "document"


def get_common_stop_words() -> set[str]:
    """Get comprehensive set of common English stop words.

    Returns an extensive set of stop words to filter out during keyword
    extraction, improving the quality of extracted terms.

    Returns:
        set[str]: Set of common English stop words
    """
    return {
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
        "there",
        "their",
        "they",
        "then",
    }
