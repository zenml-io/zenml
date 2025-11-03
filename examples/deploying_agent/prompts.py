"""Prompt components and builder for LLM-based document analysis."""

SYSTEM_PROMPT: str = "You are a document analysis assistant. Always respond with valid JSON in the exact format requested."

ANALYSIS_REQUEST: str = """
Respond with a JSON object containing:
- summary: A concise 2-3 sentence summary
- keywords: Array of 5 relevant keywords
- sentiment: One of "positive", "negative", or "neutral"
- readability: One of "easy", "medium", or "hard"
""".strip()

EXAMPLE_JSON: str = '{"summary": "This document discusses...", "keywords": ["ai", "machine", "learning", "data", "analysis"], "sentiment": "positive", "readability": "medium"}'


def build_analysis_prompt(filename: str, content_preview: str) -> str:
    """Construct the user message prompt for the analysis request.

    Args:
        filename: The document filename for context.
        content_preview: The pre-cleaned, truncated content preview.

    Returns:
        A formatted prompt string containing instructions and an example.
    """
    return f"""Analyze this document and provide structured analysis in JSON format.

Document: {filename}
Content: {content_preview}

{ANALYSIS_REQUEST}

Example:
{EXAMPLE_JSON}"""
