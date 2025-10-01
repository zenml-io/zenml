"""HTML report rendering steps for ZenML pipeline.

This module contains steps responsible for generating rich HTML reports
from document analysis results, providing visual summaries for the
ZenML dashboard.
"""

from pathlib import Path
from typing import Annotated

from models import DocumentAnalysis

from zenml import step
from zenml.types import HTMLString


@step
def render_analysis_report_step(
    analysis: DocumentAnalysis,
) -> Annotated[HTMLString, "document_analysis_report"]:
    """Render document analysis results as styled HTML report.

    Creates a comprehensive HTML report displaying all analysis results
    in a visually appealing format for the ZenML dashboard. The report
    includes document metadata, analysis metrics, and formatted content.

    Template files are loaded from the templates/ directory for easier
    customization and better separation of concerns.

    Args:
        analysis: Complete document analysis results

    Returns:
        HTMLString: Styled HTML report ready for dashboard display

    Example:
        >>> analysis = DocumentAnalysis(...)
        >>> html_report = render_analysis_report_step(analysis)
        >>> # HTML report will be displayed in ZenML dashboard
    """
    # Get template directory path relative to this file
    template_dir = Path(__file__).parent / "templates"

    # Load CSS and HTML templates
    css_path = template_dir / "report.css"
    html_path = template_dir / "report.html"

    with open(css_path, "r") as f:
        css_content = f.read()

    with open(html_path, "r") as f:
        html_template = f.read()

    # Prepare data for template
    keywords_html = ", ".join(analysis.keywords)
    formatted_timestamp = analysis.created_at.strftime("%Y-%m-%d %H:%M:%S")

    # Determine sentiment color for styling
    sentiment_colors = {
        "positive": "#10b981",  # green
        "negative": "#ef4444",  # red
        "neutral": "#6b7280",  # gray
    }
    sentiment_color = sentiment_colors.get(
        analysis.sentiment.lower(), "#6b7280"
    )

    # Format readability score as percentage
    readability_percentage = f"{analysis.readability_score * 100:.1f}%"

    # Get analysis method from metadata
    analysis_method = analysis.metadata.get("analysis_method", "unknown")
    method_display = {
        "llm": "🤖 AI-Powered",
        "deterministic": "🔧 Rule-Based",
        "deterministic_fallback": "🔧 Rule-Based (Fallback)",
    }.get(analysis_method, "Unknown")

    # Populate template with data
    html_content = html_template.format(
        css_content=css_content,
        sentiment_color=sentiment_color,
        filename=analysis.document.filename,
        timestamp=formatted_timestamp,
        word_count=f"{analysis.word_count:,}",
        sentiment=analysis.sentiment.title(),
        readability=readability_percentage,
        latency=analysis.latency_ms,
        summary=analysis.summary,
        keywords=keywords_html,
        method_display=method_display,
        model=analysis.model,
        document_type=analysis.document.document_type.title(),
        tokens_prompt=f"{analysis.tokens_prompt:,}",
        tokens_completion=f"{analysis.tokens_completion:,}",
    )

    return HTMLString(html_content)
