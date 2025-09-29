"""Simple prompt optimization pipeline for ZenML artifact management demo."""

from typing import Any, Dict, List, Optional

from models import AgentConfig, DataSourceConfig, ScoringConfig
from steps import compare_prompts_and_tag_best, ingest_data

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline
def prompt_optimization_pipeline(
    source_config: DataSourceConfig,
    prompt_variants: List[str],
    agent_config: Optional[AgentConfig] = None,
    scoring_config: Optional[ScoringConfig] = None,
) -> Dict[str, Any]:
    """Optimize prompts and tag the best one for production use.

    This pipeline demonstrates ZenML's artifact management by testing
    multiple prompt variants and tagging the best performer.

    Args:
        source_config: Data source configuration
        prompt_variants: List of prompt strings to test
        agent_config: AI agent configuration
        scoring_config: Optional scoring configuration controlling ranking

    Returns:
        Pipeline results with best prompt, scoreboard, effective scoring config, and metadata.
    """
    logger.info("🧪 Starting prompt optimization pipeline")

    # Step 1: Load data
    dataset_df, metadata = ingest_data(source_config=source_config)

    # Use a single ScoringConfig instance for both the step and return payload
    effective_scoring = scoring_config or ScoringConfig()

    # Step 2: Test prompts and tag the best one, collecting a scoreboard
    best_prompt, scoreboard = compare_prompts_and_tag_best(
        dataset_df=dataset_df,
        prompt_variants=prompt_variants,
        agent_config=agent_config,
        scoring_config=effective_scoring,
    )

    logger.info(
        "✅ Prompt optimization completed - best prompt tagged and scoreboard generated"
    )

    return {
        "best_prompt": best_prompt,
        "scoreboard": [entry.model_dump() for entry in scoreboard],
        "scoring": effective_scoring.model_dump(),
        "metadata": metadata,
        "config": {
            "source": f"{source_config.source_type}:{source_config.source_path}",
            "variants_tested": len(prompt_variants),
        },
    }
