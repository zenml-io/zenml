"""HTML report rendering steps for ZenML pipeline.

This module contains steps responsible for generating rich HTML reports
from document analysis results, providing visual summaries for the
ZenML dashboard.
"""

from typing import Annotated

from models import DocumentAnalysis

from zenml import step
from zenml.logger import get_logger
from zenml.types import HTMLString

# Get ZenML logger for consistent logging
logger = get_logger(__name__)


@step
def render_analysis_report_step(
    analysis: DocumentAnalysis,
) -> Annotated[HTMLString, "document_analysis_report"]:
    """Render document analysis results as styled HTML report.

    Creates a comprehensive HTML report displaying all analysis results
    in a visually appealing format for the ZenML dashboard. The report
    includes document metadata, analysis metrics, and formatted content.

    Args:
        analysis: Complete document analysis results

    Returns:
        HTMLString: Styled HTML report ready for dashboard display

    Example:
        >>> analysis = DocumentAnalysis(...)
        >>> html_report = render_analysis_report_step(analysis)
        >>> # HTML report will be displayed in ZenML dashboard
    """
    logger.info(
        f"Rendering HTML report for document: {analysis.document.filename}"
    )

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

    logger.debug(
        f"Report data prepared: {len(keywords_html)} char keywords, method={analysis_method}"
    )

    # Read CSS content for inline inclusion
    css_path = "static/css/report.css"
    try:
        with open(css_path, "r") as f:
            css_content = f.read()
    except FileNotFoundError:
        logger.warning(
            f"CSS file not found at {css_path}, using fallback styles"
        )
        css_content = "/* Fallback styles */ body { font-family: Arial, sans-serif; margin: 20px; }"

    # Generate comprehensive HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document Analysis Report - {analysis.document.filename}</title>
        <style>
          {css_content}
          .sentiment {{ color: {sentiment_color}; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>📄 Document Analysis Report</h1>
            <p>Comprehensive analysis of <strong>{analysis.document.filename}</strong></p>
            <p>Generated on {formatted_timestamp}</p>
          </div>
          
          <div class="content">
            <div class="section">
              <h2>📊 Key Metrics</h2>
              <div class="metrics-grid">
                <div class="metric">
                  <span class="metric-value">{analysis.word_count:,}</span>
                  <div class="metric-label">Words</div>
                </div>
                <div class="metric">
                  <span class="metric-value sentiment">{analysis.sentiment.title()}</span>
                  <div class="metric-label">Sentiment</div>
                </div>
                <div class="metric">
                  <span class="metric-value">{readability_percentage}</span>
                  <div class="metric-label">Readability</div>
                </div>
                <div class="metric">
                  <span class="metric-value processing-time">{analysis.latency_ms}ms</span>
                  <div class="metric-label">Processing Time</div>
                </div>
              </div>
            </div>
            
            <div class="section">
              <h2>📝 Summary</h2>
              <div class="summary-box">
                {analysis.summary}
              </div>
            </div>
            
            <div class="section">
              <h2>🏷️ Keywords</h2>
              <div class="keywords-container">
                <div class="keywords">{keywords_html}</div>
              </div>
            </div>
            
            <div class="section">
              <h2>⚙️ Processing Details</h2>
              <div class="metadata-grid">
                <div class="metadata-item">
                  <span class="metadata-label">Analysis Method:</span>
                  <span class="metadata-value">{method_display}</span>
                </div>
                <div class="metadata-item">
                  <span class="metadata-label">Model:</span>
                  <span class="metadata-value">{analysis.model}</span>
                </div>
                <div class="metadata-item">
                  <span class="metadata-label">Document Type:</span>
                  <span class="metadata-value">{analysis.document.document_type.title()}</span>
                </div>
                <div class="metadata-item">
                  <span class="metadata-label">Analysis Type:</span>
                  <span class="metadata-value">{analysis.document.analysis_type.title()}</span>
                </div>
                <div class="metadata-item">
                  <span class="metadata-label">Prompt Tokens:</span>
                  <span class="metadata-value">{analysis.tokens_prompt:,}</span>
                </div>
                <div class="metadata-item">
                  <span class="metadata-label">Completion Tokens:</span>
                  <span class="metadata-value">{analysis.tokens_completion:,}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="footer">
            <span class="badge">ZenML Document Analysis Pipeline</span>
            <br>
            Generated with ❤️ by ZenML • Processing completed in {analysis.latency_ms}ms
          </div>
        </div>
      </body>
    </html>
    """.strip()

    logger.info(
        f"HTML report generated successfully ({len(html_content):,} characters)"
    )

    return HTMLString(html_content)
