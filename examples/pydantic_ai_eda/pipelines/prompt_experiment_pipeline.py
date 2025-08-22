"""Pipeline for experimenting with Pydantic AI agent prompts."""

from typing import Any, Dict, List, Optional

from models import AgentConfig, DataSourceConfig
from steps import compare_agent_prompts, ingest_data

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline
def prompt_experiment_pipeline(
    source_config: DataSourceConfig,
    prompt_variants: List[str],
    agent_config: Optional[AgentConfig] = None,
) -> Dict[str, Any]:
    """Pipeline for A/B testing Pydantic AI agent prompts.
    
    This pipeline helps developers optimize their agent prompts by testing
    multiple variants on the same dataset and comparing performance metrics.
    
    Args:
        source_config: Data source to test prompts against  
        prompt_variants: List of system prompts to compare
        agent_config: Configuration for agent behavior during testing
        
    Returns:
        Comprehensive comparison results with recommendations
    """
    logger.info(f"🧪 Starting prompt experiment with {len(prompt_variants)} variants")
    
    # Step 1: Load the test dataset
    dataset_df, ingestion_metadata = ingest_data(source_config=source_config)
    
    # Step 2: Run prompt comparison experiment
    experiment_results = compare_agent_prompts(
        dataset_df=dataset_df,
        prompt_variants=prompt_variants,
        agent_config=agent_config,
    )
    
    logger.info("✅ Prompt experiment completed - check results for best performing variant")
    
    return {
        "experiment_results": experiment_results,
        "dataset_metadata": ingestion_metadata,
        "test_config": {
            "source": f"{source_config.source_type}:{source_config.source_path}",
            "prompt_count": len(prompt_variants),
            "agent_config": agent_config.model_dump() if agent_config else None,
        },
    }