"""EDA pipeline using Pydantic AI for automated data analysis.

This pipeline orchestrates the complete EDA workflow:
1. Data ingestion from various sources
2. AI-powered EDA analysis with Pydantic AI
3. Quality gate evaluation for pipeline routing
"""

from typing import Any, Dict, Optional

from models import AgentConfig, DataSourceConfig
from steps import (
    evaluate_quality_gate,
    ingest_data,
    route_based_on_quality,
    run_eda_agent,
)

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline
def eda_pipeline(
    source_config: DataSourceConfig,
    agent_config: Optional[AgentConfig] = None,
    min_quality_score: float = 70.0,
    block_on_high_severity: bool = True,
    max_missing_data_pct: float = 30.0,
    require_target_column: bool = False,
) -> Dict[str, Any]:
    """Complete EDA pipeline with AI-powered analysis and quality gating.

    Performs end-to-end exploratory data analysis using Pydantic AI,
    from data ingestion through quality assessment and routing decisions.

    Args:
        source_config: Configuration for data source (HuggingFace/local/warehouse)
        agent_config: Configuration for Pydantic AI agent behavior
        min_quality_score: Minimum quality score for passing quality gate
        block_on_high_severity: Whether high-severity issues block the pipeline
        max_missing_data_pct: Maximum allowable missing data percentage
        require_target_column: Whether to require a target column for analysis

    Returns:
        Dictionary containing all pipeline outputs and routing decisions
    """
    logger.info(
        f"Starting EDA pipeline for {source_config.source_type}:{source_config.source_path}"
    )

    # Step 1: Ingest data from configured source
    raw_df, ingestion_metadata = ingest_data(source_config=source_config)

    # Step 2: Run AI-powered EDA analysis
    report_markdown, report_json, sql_log, analysis_tables = run_eda_agent(
        dataset_df=raw_df,
        dataset_metadata=ingestion_metadata,
        agent_config=agent_config,
    )

    # Step 3: Evaluate data quality gate
    quality_decision = evaluate_quality_gate(
        report_json=report_json,
        min_quality_score=min_quality_score,
        block_on_high_severity=block_on_high_severity,
        max_missing_data_pct=max_missing_data_pct,
        require_target_column=require_target_column,
        target_column=source_config.target_column,
    )

    # Step 4: Route based on quality assessment
    routing_message = route_based_on_quality(
        decision=quality_decision,
        on_pass_message="Data quality acceptable - ready for downstream processing",
        on_fail_message="Data quality insufficient - requires remediation before use",
    )

    # Log pipeline summary (note: artifacts are returned, actual values logged in steps)
    logger.info("Pipeline steps completed successfully")
    logger.info("Check step outputs for detailed analysis results")

    # Return comprehensive results
    return {
        # Core analysis outputs
        "report_markdown": report_markdown,
        "report_json": report_json,
        "analysis_tables": analysis_tables,
        "sql_log": sql_log,
        # Graph visualization removed
        # Quality assessment
        "quality_decision": quality_decision,
        "routing_message": routing_message,
        # Pipeline metadata
        "source_config": source_config,
        "ingestion_metadata": ingestion_metadata,
        "agent_config": agent_config,
        # Summary metrics (basic info only, artifacts available separately)
        "pipeline_summary": {
            "data_source": f"{source_config.source_type}:{source_config.source_path}",
            "target_column": source_config.target_column,
            "timestamp": ingestion_metadata,  # This will be the artifact
        },
    }
