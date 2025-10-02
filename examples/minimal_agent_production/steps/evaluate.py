"""Evaluation steps for document analysis quality assessment.

This module contains steps for evaluating the quality of document analysis
outputs, including loading analyses from the model registry, annotation,
and report generation.
"""

from typing import Annotated, List

from models import (
    AnalysisAnnotation,
    AnnotatedAnalysis,
    DocumentAnalysis,
    EvaluationReport,
)

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger
from zenml.types import HTMLString

# Get ZenML logger for consistent logging
logger = get_logger(__name__)


@step(enable_cache=False)
def load_recent_analyses(max_items: int = 20) -> List[DocumentAnalysis]:
    """Load recent document analyses for evaluation.

    Fetches the most recent DocumentAnalysis artifacts by name from the
    document_analysis_agent model for quality assessment and evaluation.

    Args:
        max_items: Maximum number of analyses to load

    Returns:
        List of DocumentAnalysis objects for evaluation
    """
    client = Client()
    analyses: List[DocumentAnalysis] = []

    try:
        # Get the document analysis model
        model_version = client.get_model_version(
            "document_analysis_agent", "production"
        )

        # Get artifact versions by name from the model
        artifact_versions = client.list_artifact_versions(
            name="document_analysis",
            sort_by="desc:created",
            size=max_items,
            model_version_id=model_version.id,
        )

        logger.info(
            f"Found {len(artifact_versions)} document_analysis artifacts"
        )

        for artifact_version in artifact_versions:
            try:
                # Load the artifact directly by its version
                analysis = artifact_version.load()
                if isinstance(analysis, DocumentAnalysis):
                    analyses.append(analysis)
                    logger.debug(
                        f"Loaded analysis for: {analysis.document.filename}"
                    )

                if len(analyses) >= max_items:
                    break

            except Exception as e:
                logger.warning(
                    f"Failed to load artifact version {artifact_version.id}: {e}"
                )
                continue

        logger.info(
            f"Successfully loaded {len(analyses)} document analyses for evaluation"
        )
        return analyses

    except Exception as e:
        logger.warning(
            f"Failed to load analyses from model, returning empty list: {e}"
        )
        return []


def _annotate_analysis(analysis: DocumentAnalysis) -> AnalysisAnnotation:
    """Annotate a document analysis with quality scores.

    Args:
        analysis: The document analysis to evaluate

    Returns:
        Quality annotation for the analysis
    """
    # Evaluate summary quality (basic heuristics)
    summary_quality = (
        len(analysis.summary) > 20
        and not analysis.summary.startswith("N/A")
        and "." in analysis.summary
    )

    # Evaluate keyword relevance
    keywords_relevant = (
        len(analysis.keywords) >= 3
        and not all(k.startswith("term") for k in analysis.keywords)
        and len(set(analysis.keywords))
        == len(analysis.keywords)  # No duplicates
    )

    # Evaluate sentiment accuracy (check for valid sentiment)
    sentiment_accurate = analysis.sentiment.lower() in [
        "positive",
        "negative",
        "neutral",
    ]

    # Evaluate completeness (all fields present and reasonable)
    analysis_complete = (
        analysis.word_count > 0
        and 0.0 <= analysis.readability_score <= 1.0
        and analysis.latency_ms > 0
    )

    return AnalysisAnnotation(
        summary_quality=summary_quality,
        keywords_relevant=keywords_relevant,
        sentiment_accurate=sentiment_accurate,
        analysis_complete=analysis_complete,
        notes=None,
    )


@step
def annotate_analyses_step(
    analyses: List[DocumentAnalysis],
) -> Annotated[List[AnnotatedAnalysis], "annotated_analyses"]:
    """Annotate document analyses with quality assessments.

    Applies automated quality scoring to document analyses using
    rule-based evaluation criteria. Evaluates summary quality,
    keyword relevance, sentiment accuracy, and analysis completeness.

    Args:
        analyses: List of document analyses to annotate

    Returns:
        List of annotated analyses with quality scores

    Example:
        >>> analyses = [DocumentAnalysis(...), ...]
        >>> annotated = annotate_analyses_step(analyses)
        >>> print(f"Annotated {len(annotated)} analyses")
    """
    logger.info(f"Starting annotation of {len(analyses)} analyses")

    if not analyses:
        logger.warning("No analyses provided for annotation")
        return []

    annotated_results = []
    for analysis in analyses:
        try:
            annotation = _annotate_analysis(analysis)
            annotated_results.append(
                AnnotatedAnalysis(analysis=analysis, annotation=annotation)
            )
        except Exception as e:
            logger.error(
                f"Failed to annotate analysis for {analysis.document.filename}: {e}"
            )
            continue

    # Log summary statistics
    if annotated_results:
        total = len(annotated_results)
        quality_scores = {
            "summary_quality": sum(
                1 for a in annotated_results if a.annotation.summary_quality
            )
            / total,
            "keywords_relevant": sum(
                1 for a in annotated_results if a.annotation.keywords_relevant
            )
            / total,
            "sentiment_accurate": sum(
                1 for a in annotated_results if a.annotation.sentiment_accurate
            )
            / total,
            "analysis_complete": sum(
                1 for a in annotated_results if a.annotation.analysis_complete
            )
            / total,
        }

        logger.info(
            f"Annotation completed: {total} analyses processed. "
            f"Quality scores: {quality_scores}"
        )

    return annotated_results


@step
def aggregate_evaluation_results_step(
    annotated: List[AnnotatedAnalysis],
) -> Annotated[EvaluationReport, "evaluation_report"]:
    """Aggregate annotations into evaluation report.

    Compiles individual analysis annotations into summary statistics
    and generates an HTML report for visualization. Creates comprehensive
    quality metrics and detailed per-document results.

    Args:
        annotated: List of annotated document analyses

    Returns:
        EvaluationReport with aggregated scores and HTML report

    Example:
        >>> annotated = [AnnotatedAnalysis(...), ...]
        >>> report = aggregate_evaluation_results_step(annotated)
        >>> print(f"Report covers {report.total} analyses")
    """
    logger.info(
        f"Aggregating evaluation results for {len(annotated)} annotated analyses"
    )

    if not annotated:
        logger.warning("No annotated analyses provided for aggregation")
        return EvaluationReport(
            total=0,
            scores={},
            by_item=[],
            html_report="<p>No document analyses found for evaluation.</p>",
        )

    total = len(annotated)
    sums = {
        "summary_quality": sum(
            1 for a in annotated if a.annotation.summary_quality
        ),
        "keywords_relevant": sum(
            1 for a in annotated if a.annotation.keywords_relevant
        ),
        "sentiment_accurate": sum(
            1 for a in annotated if a.annotation.sentiment_accurate
        ),
        "analysis_complete": sum(
            1 for a in annotated if a.annotation.analysis_complete
        ),
    }
    scores = {k: v / total for k, v in sums.items()}

    logger.info(f"Calculated aggregate scores: {scores}")

    # Generate HTML table rows for individual results
    rows = []
    for item in annotated:
        filename = item.analysis.document.filename[:30] + (
            "..." if len(item.analysis.document.filename) > 30 else ""
        )
        rows.append(
            f"<tr><td>{filename}</td>"
            f"<td>{'✅' if item.annotation.summary_quality else '❌'}</td>"
            f"<td>{'✅' if item.annotation.keywords_relevant else '❌'}</td>"
            f"<td>{'✅' if item.annotation.sentiment_accurate else '❌'}</td>"
            f"<td>{'✅' if item.annotation.analysis_complete else '❌'}</td>"
            f"<td>{item.analysis.word_count}</td>"
            f"<td>{item.analysis.sentiment}</td>"
            f"<td>{item.analysis.readability_score:.2f}</td>"
            f"</tr>"
        )

    # Read CSS content for inline inclusion
    css_path = "static/css/evaluation.css"
    try:
        with open(css_path, "r") as f:
            css_content = f.read()
    except FileNotFoundError:
        logger.warning(
            f"CSS file not found at {css_path}, using fallback styles"
        )
        css_content = "/* Fallback styles */ body { font-family: Arial, sans-serif; margin: 20px; }"

    # Generate comprehensive HTML report
    html = f"""
    <html>
      <head>
        <title>Document Analysis Evaluation</title>
        <style>
          {css_content}
        </style>
      </head>
      <body>
        <h2>📊 Document Analysis Evaluation Report</h2>
        <div class="summary">
          <p><strong>Total analyses evaluated:</strong> {total}</p>
          <p><strong>Overall quality score:</strong> {sum(scores.values()) / len(scores):.1%}</p>
        </div>
        
        <h3>Quality Metrics</h3>
        <div>
          <span class="metric">Summary Quality: {scores["summary_quality"]:.1%}</span>
          <span class="metric">Keywords Relevant: {scores["keywords_relevant"]:.1%}</span>
          <span class="metric">Sentiment Accurate: {scores["sentiment_accurate"]:.1%}</span>
          <span class="metric">Analysis Complete: {scores["analysis_complete"]:.1%}</span>
        </div>
        
        <h3>Individual Analysis Results</h3>
        <table>
          <thead>
            <tr>
              <th>Document</th>
              <th>Summary Quality</th>
              <th>Keywords Relevant</th>
              <th>Sentiment Accurate</th>
              <th>Analysis Complete</th>
              <th>Word Count</th>
              <th>Sentiment</th>
              <th>Readability</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows)}
          </tbody>
        </table>
        
        <div class="summary">
          <p><em>Generated by ZenML Document Analysis Evaluation Pipeline</em></p>
        </div>
      </body>
    </html>
    """.strip()

    report = EvaluationReport(
        total=total, scores=scores, by_item=annotated, html_report=html
    )

    logger.info(f"Generated evaluation report for {total} analyses")
    return report


@step
def render_evaluation_report_step(
    report: EvaluationReport,
) -> Annotated[HTMLString, "evaluation_report_html"]:
    """Render evaluation report as HTML string artifact.

    Converts the evaluation report into an HTMLString artifact
    for dashboard display and visualization in the ZenML UI.

    Args:
        report: The evaluation report to render

    Returns:
        HTMLString containing the formatted report for artifact storage

    Example:
        >>> report = EvaluationReport(...)
        >>> html_artifact = render_evaluation_report_step(report)
        >>> print(type(html_artifact))  # <class 'zenml.types.HTMLString'>
    """
    logger.info(f"Rendering evaluation report for {report.total} analyses")

    if not report.html_report:
        logger.warning("No HTML report content found, using fallback message")
        html_content = "<p>No evaluation report content available.</p>"
    else:
        html_content = report.html_report

    html_string = HTMLString(html_content)
    logger.info(
        "Successfully rendered evaluation report as HTMLString artifact"
    )

    return html_string
