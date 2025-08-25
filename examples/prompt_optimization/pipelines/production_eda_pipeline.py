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
    """Production EDA pipeline using optimized prompts from the registry.

    This pipeline demonstrates ZenML's artifact retrieval by fetching
    previously optimized prompts for production analysis.

    Args:
        source_config: Data source configuration
        agent_config: AI agent configuration
        use_optimized_prompt: Whether to use optimized prompt from registry

    Returns:
        EDA results and metadata
    """
    logger.info("🏭 Starting production EDA pipeline")

    # Step 1: Get optimized prompt
    optimized_prompt = get_optimized_prompt()
    logger.info("🎯 Retrieved optimized prompt")

    # Step 2: Load data
    dataset_df, metadata = ingest_data(source_config=source_config)

    # Step 3: Run EDA analysis with optimized prompt
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
        "used_optimized_prompt": optimized_prompt is not None,
        "metadata": metadata,
    }
