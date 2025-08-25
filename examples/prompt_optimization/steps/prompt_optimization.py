"""Simple prompt optimization step for demonstrating ZenML artifact management."""

import time
from typing import Annotated

import pandas as pd
from models import AgentConfig, EDAReport
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from steps.agent_tools import AGENT_TOOLS, AnalystAgentDeps

from zenml import ArtifactConfig, ExternalArtifact, Tag, add_tags, step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def compare_prompts_and_tag_best(
    dataset_df: pd.DataFrame,
    prompt_variants: list[str],
    agent_config: AgentConfig = None,
) -> Annotated[str, ArtifactConfig(name="best_prompt")]:
    """Compare prompt variants and tag the best one with exclusive 'optimized' tag.
    
    This step demonstrates ZenML's artifact management by:
    1. Testing multiple prompt variants
    2. Finding the best performer 
    3. Returning it as a tagged artifact that other pipelines can find
    
    The 'optimized' tag is exclusive, so only one prompt can be 'optimized' at a time.
    
    Args:
        dataset_df: Dataset to test prompts against
        prompt_variants: List of system prompts to compare
        agent_config: Configuration for AI agents
        
    Returns:
        The best performing prompt string with exclusive 'optimized' tag
    """
    if agent_config is None:
        agent_config = AgentConfig()

    logger.info(f"🧪 Testing {len(prompt_variants)} prompt variants")
    
    results = []
    
    for i, system_prompt in enumerate(prompt_variants):
        prompt_id = f"variant_{i + 1}"
        logger.info(f"Testing {prompt_id}...")
        
        start_time = time.time()
        
        try:
            # Create agent with this prompt
            deps = AnalystAgentDeps()
            main_ref = deps.store(dataset_df)
            
            agent = Agent(
                f"openai:{agent_config.model_name}",
                deps_type=AnalystAgentDeps,
                output_type=EDAReport,
                system_prompt=system_prompt,
                model_settings=ModelSettings(parallel_tool_calls=False),
            )
            
            for tool in AGENT_TOOLS:
                agent.tool(tool)
            
            # Run analysis
            user_prompt = f"Analyze dataset '{main_ref}' - focus on data quality and key insights."
            result = agent.run_sync(user_prompt, deps=deps)
            eda_report = result.output
            
            execution_time = time.time() - start_time
            
            # Score this variant
            score = (
                eda_report.data_quality_score * 0.7 +  # Primary metric
                (100 - min(execution_time * 2, 100)) * 0.2 +  # Speed bonus
                len(eda_report.key_findings) * 5 * 0.1  # Thoroughness
            )
            
            results.append({
                "prompt_id": prompt_id,
                "prompt": system_prompt,
                "score": score,
                "quality_score": eda_report.data_quality_score,
                "execution_time": execution_time,
                "findings_count": len(eda_report.key_findings),
                "success": True,
            })
            
            logger.info(f"✅ {prompt_id}: score={score:.1f}, time={execution_time:.1f}s")
            
        except Exception as e:
            logger.warning(f"❌ {prompt_id} failed: {e}")
            results.append({
                "prompt_id": prompt_id,
                "prompt": system_prompt,
                "score": 0,
                "success": False,
                "error": str(e),
            })
    
    # Find best performer
    successful_results = [r for r in results if r["success"]]
    
    if not successful_results:
        logger.warning("All prompts failed, using first as fallback")
        best_prompt = prompt_variants[0]
    else:
        best_result = max(successful_results, key=lambda x: x["score"])
        best_prompt = best_result["prompt"]
        logger.info(f"🏆 Best prompt: {best_result['prompt_id']} (score: {best_result['score']:.1f})")
    
    logger.info("💾 Best prompt will be stored with exclusive 'optimized' tag")
    
    # Add exclusive tag to this step's output artifact
    add_tags(
        tags=[Tag(name="optimized", exclusive=True)],
        infer_artifact=True
    )
    
    return best_prompt


def get_optimized_prompt():
    """Retrieve the optimized prompt using ZenML's tag-based filtering.
    
    This demonstrates ZenML's tag filtering by finding artifacts tagged with 'optimized'.
    Since 'optimized' is an exclusive tag, there will be at most one such artifact.
    
    Returns:
        The optimized prompt from the latest optimization run, or default if none found
    """
    try:
        client = Client()
        
        # Find artifacts tagged with 'optimized' (our exclusive tag)
        artifacts = client.list_artifact_versions(
            tags=["optimized"],
            size=1
        )
        
        if artifacts.items:
            optimized_prompt = artifacts.items[0]
            logger.info(f"🎯 Retrieved optimized prompt from artifact: {optimized_prompt.id}")
            logger.info(f"   Artifact created: {optimized_prompt.created}")
            return optimized_prompt
        else:
            logger.info("🔍 No optimized prompt found (no artifacts with 'optimized' tag)")
            
    except Exception as e:
        logger.warning(f"Failed to retrieve optimized prompt: {e}")
    
    # Fallback to default prompt if no optimization artifacts found
    logger.info("📝 Using default prompt (run optimization pipeline first)")
    default_prompt = """You are a data analyst. Perform comprehensive EDA analysis.

FOCUS ON:
- Calculate data quality score (0-100) based on completeness and consistency  
- Identify missing data patterns and duplicates
- Find key correlations and patterns
- Provide 3-5 actionable recommendations

Be thorough but efficient."""
    
    return ExternalArtifact(value=default_prompt)