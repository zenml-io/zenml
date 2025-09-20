"""HTML report rendering steps for ZenML pipeline.

This module contains steps responsible for generating rich HTML reports
from document analysis results, providing visual summaries for the
ZenML dashboard.
"""

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

    Args:
        analysis: Complete document analysis results

    Returns:
        HTMLString: Styled HTML report ready for dashboard display

    Example:
        >>> analysis = DocumentAnalysis(...)
        >>> html_report = render_analysis_report_step(analysis)
        >>> # HTML report will be displayed in ZenML dashboard
    """
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

    # Inline CSS styles for the report
    css_content = """
    /* Document Analysis Report Styles */
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      line-height: 1.6;
      margin: 0;
      padding: 20px;
      background-color: #f8fafc;
      color: #1e293b;
    }
    .container {
      max-width: 800px;
      margin: 0 auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
      overflow: hidden;
    }
    .header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 24px;
      text-align: center;
    }
    .header h1 {
      margin: 0 0 8px 0;
      font-size: 24px;
      font-weight: 600;
    }
    .header p {
      margin: 0;
      opacity: 0.9;
      font-size: 14px;
    }
    .content {
      padding: 24px;
    }
    .section {
      margin-bottom: 32px;
    }
    .section:last-child {
      margin-bottom: 0;
    }
    .section h2 {
      font-size: 18px;
      font-weight: 600;
      margin: 0 0 16px 0;
      color: #1e293b;
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 8px;
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin: 16px 0;
    }
    .metric {
      background: #f1f5f9;
      padding: 16px;
      border-radius: 8px;
      text-align: center;
      border-left: 4px solid #3b82f6;
    }
    .metric-value {
      font-size: 24px;
      font-weight: 700;
      color: #1e293b;
      display: block;
    }
    .metric-label {
      font-size: 12px;
      color: #64748b;
      text-transform: uppercase;
      font-weight: 500;
      letter-spacing: 0.05em;
      margin-top: 4px;
    }
    .sentiment {
      font-weight: 600;
    }
    .summary-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-left: 4px solid #3b82f6;
      padding: 20px;
      border-radius: 0 8px 8px 0;
      font-style: italic;
      line-height: 1.7;
    }
    .keywords-container {
      background: #fef3c7;
      padding: 16px;
      border-radius: 8px;
      border: 1px solid #fbbf24;
    }
    .keywords {
      font-weight: 500;
      color: #92400e;
    }
    .metadata-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      background: #f1f5f9;
      padding: 16px;
      border-radius: 8px;
    }
    .metadata-item {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
    }
    .metadata-label {
      font-weight: 500;
      color: #64748b;
    }
    .metadata-value {
      font-weight: 600;
      color: #1e293b;
    }
    .footer {
      background: #f1f5f9;
      padding: 16px 24px;
      border-top: 1px solid #e2e8f0;
      font-size: 12px;
      color: #64748b;
      text-align: center;
    }
    .badge {
      display: inline-block;
      background: #3b82f6;
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 500;
    }
    .processing-time {
      color: #059669;
      font-weight: 600;
    }
    """

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

    return HTMLString(html_content)
