"""Simple production EDA pipeline using optimized prompts."""

from typing import Any, Dict, Optional

from models import AgentConfig, DataSourceConfig
from steps import get_optimized_prompt, ingest_data, run_eda_agent

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline
def production_eda_pipeline(
    source_config: DataSourceConfig,
    agent_config: Optional[AgentConfig] = None,
) -> Dict[str, Any]:
    """Production EDA pipeline using an optimized prompt when available.

    The pipeline automatically attempts to retrieve the latest optimized prompt
    from the artifact registry (tagged 'optimized') and falls back to the
    default system prompt if none is available or retrieval fails.

    Args:
        source_config: Data source configuration
        agent_config: AI agent configuration

    Returns:
        EDA results and metadata, including whether an optimized prompt was used.
    """
    logger.info("🏭 Starting production EDA pipeline")

    # Step 1: Get optimized prompt or fall back to default
    optimized_prompt, used_optimized = get_optimized_prompt()
    if used_optimized:
        logger.info("🎯 Using optimized prompt retrieved from artifact")
    else:
        logger.warning(
            "🔍 Optimized prompt not found; falling back to default system prompt"
        )

    # Step 2: Load data
    dataset_df, metadata = ingest_data(source_config=source_config)

    # Step 3: Run EDA analysis with the selected prompt
    report_markdown, report_json, sql_log, analysis_tables = run_eda_agent(
        dataset_df=dataset_df,
        dataset_metadata=metadata,
        agent_config=agent_config,
        custom_system_prompt=optimized_prompt,
    )

    logger.info("✅ Production EDA pipeline completed")

    return {
        "report_markdown": report_markdown,
        "report_json": report_json,
        "sql_log": sql_log,
        "analysis_tables": analysis_tables,
        "used_optimized_prompt": used_optimized,
        "metadata": metadata,
    }
