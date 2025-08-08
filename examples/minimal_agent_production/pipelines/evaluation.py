"""Evaluation pipeline for document analysis quality assessment.

This module contains the pipeline definition for evaluating the quality
of document analysis outputs. Steps are imported from the steps module.
"""

from steps import (
    aggregate_evaluation_results_step,
    annotate_analyses_step,
    load_recent_analyses,
    render_evaluation_report_step,
)

from zenml import Model, pipeline
from zenml.config import DockerSettings

# All steps are now imported from the steps module


docker_settings = DockerSettings(
    requirements="requirements.txt",
    python_package_installer="uv",
)


@pipeline(
    settings={"docker": docker_settings},
    model=Model(name="document_analysis_agent", version="production"),
)
def evaluation_pipeline(max_items: int = 100) -> None:
    """End-to-end evaluation pipeline for document analysis.

    Orchestrates the complete evaluation workflow from loading
    recent document analyses through generating the final HTML report.
    Uses the ZenML Model registry to fetch analyses from the
    document_analysis_agent model.

    Args:
        max_items: Maximum number of analyses to evaluate
    """
    analyses = load_recent_analyses(max_items=max_items)
    annotated = annotate_analyses_step(analyses)
    report = aggregate_evaluation_results_step(annotated)
    render_evaluation_report_step(report)
