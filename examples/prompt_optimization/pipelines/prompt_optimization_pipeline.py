"""Simple prompt optimization pipeline for ZenML artifact management demo."""

from typing import Any, Dict, List, Optional

from models import AgentConfig, DataSourceConfig
from steps import compare_prompts_and_tag_best, ingest_data

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline
def prompt_optimization_pipeline(
    source_config: DataSourceConfig,
    prompt_variants: List[str],
    agent_config: Optional[AgentConfig] = None,
) -> Dict[str, Any]:
    """Optimize prompts and tag the best one for production use.
    
    This pipeline demonstrates ZenML's artifact management by testing
    multiple prompt variants and tagging the best performer.
    
    Args:
        source_config: Data source configuration  
        prompt_variants: List of prompt strings to test
        agent_config: AI agent configuration
        
    Returns:
        Pipeline results with best prompt and metadata
    """
    logger.info("🧪 Starting prompt optimization pipeline")
    
    # Step 1: Load data
    dataset_df, metadata = ingest_data(source_config=source_config)
    
    # Step 2: Test prompts and tag the best one
    best_prompt = compare_prompts_and_tag_best(
        dataset_df=dataset_df,
        prompt_variants=prompt_variants, 
        agent_config=agent_config,
    )
    
    logger.info("✅ Prompt optimization completed - best prompt tagged with 'optimized'")
    
    return {
        "best_prompt": best_prompt,
        "metadata": metadata,
        "config": {
            "source": f"{source_config.source_type}:{source_config.source_path}",
            "variants_tested": len(prompt_variants),
        },
    }