"""Centralized constants for the minimal agent production example.

This module exposes a flat set of constants and exactly two environment-
based overrides for ease of configuration without expanding the surface
area of runtime knobs.

Only the following environment variables are read:
- DOC_ANALYSIS_LLM_MODEL
- DOCUMENT_ANALYSIS_ENDPOINT
"""

import os

# -----------------------------------------------------------------------------
# Allowed environment-based overrides (only these read from env)
# -----------------------------------------------------------------------------
DOC_ANALYSIS_LLM_MODEL: str = os.getenv("DOC_ANALYSIS_LLM_MODEL", "gpt-5-mini")
DOCUMENT_ANALYSIS_ENDPOINT: str = os.getenv(
    "DOCUMENT_ANALYSIS_ENDPOINT", "http://localhost:8000"
)

# Optional convenience alias for UI display consistency
LLM_MODEL: str = DOC_ANALYSIS_LLM_MODEL

# -----------------------------------------------------------------------------
# LLM defaults (literals only)
# -----------------------------------------------------------------------------
LLM_TEMPERATURE: float = 0.1
LLM_MAX_TOKENS: int = 300
MODEL_LABEL_FMT: str = "openai-{model} (llm)"

# -----------------------------------------------------------------------------
# Ingestion defaults (literals only)
# -----------------------------------------------------------------------------
URL_TIMEOUT_S: int = 30
DEFAULT_DOC_TYPE: str = "text"
EXTENSION_TO_TYPE: dict[str, str] = {
    "md": "markdown",
    "txt": "text",
    "py": "text",
    "js": "text",
    "html": "text",
    "xml": "text",
    "csv": "text",
    "json": "text",
}

# -----------------------------------------------------------------------------
# UI defaults (literals only)
# -----------------------------------------------------------------------------
REQUEST_TIMEOUT_S: int = 120
INVOKE_SUFFIX: str = "/invoke"
UI_PREVIEW_MAX_CHARS: int = 1000
READABILITY_EASY_GT: float = 0.7
READABILITY_MEDIUM_GT: float = 0.4
SENTIMENT_EMOJI: dict[str, str] = {
    "positive": "😊",
    "negative": "😞",
    "neutral": "😐",
}
UPLOAD_FILE_TYPES: list[str] = [
    "txt",
    "md",
    "csv",
    "json",
    "py",
    "js",
    "html",
    "xml",
]

# -----------------------------------------------------------------------------
# Rendering constants (literals only)
# -----------------------------------------------------------------------------
TEMPLATE_CSS_FILENAME: str = "report.css"
TEMPLATE_HTML_FILENAME: str = "report.html"

SENTIMENT_COLORS: dict[str, str] = {
    "positive": "#10b981",  # green
    "negative": "#ef4444",  # red
    "neutral": "#6b7280",  # gray
}

# Preferred key for method labels
METHOD_LABELS: dict[str, str] = {
    "llm": "🤖 AI-Powered",
    "deterministic": "🔧 Rule-Based",
    "deterministic_fallback": "🔧 Rule-Based (Fallback)",
}
# Backwards-compatible alias (used by render.py)
METHOD_DISPLAY_MAP: dict[str, str] = METHOD_LABELS

# -----------------------------------------------------------------------------
# Text heuristics (literals only)
# -----------------------------------------------------------------------------
KEYWORD_COUNT: int = 5
CONTENT_PREVIEW_CHARS: int = 2000
READABILITY_SCORE_MAP: dict[str, float] = {
    "easy": 0.9,
    "medium": 0.6,
    "hard": 0.3,
}
MIN_MEANINGFUL_PARAGRAPH_LEN: int = 50
MAX_SUMMARY_CHARS: int = 200
MAX_SUMMARY_SENTENCES: int = 3
