"""Simple prompt optimization step for demonstrating ZenML artifact management."""

import time
from typing import Annotated

import pandas as pd
from models import AgentConfig, EDAReport
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from steps.agent_tools import AGENT_TOOLS, AnalystAgentDeps
from steps.prompt_text import DEFAULT_SYSTEM_PROMPT, build_user_prompt

from zenml import ArtifactConfig, Tag, add_tags, step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

# Scoring weights reflect priorities: quality first (insightful outputs),
# then speed (encourage lower latency), then findings (reward coverage).
WEIGHT_QUALITY: float = 0.7
WEIGHT_SPEED: float = 0.2
WEIGHT_FINDINGS: float = 0.1

# Linear time penalty: each second reduces the speed score by this many points
# until the score floors at 0 (capped at 100 points of penalty).
SPEED_PENALTY_PER_SECOND: float = 2.0

# Reward per key finding discovered by the agent before applying the findings weight.
# Keeping this explicit makes it easy to tune coverage incentives.
FINDINGS_SCORE_PER_ITEM: float = 0.5


def compute_prompt_score(
    eda_report: EDAReport, execution_time: float
) -> float:
    """Compute a prompt's score from EDA results and runtime.

    This makes scoring trade-offs explicit and tunable via module-level constants:
    - Prioritize report quality (WEIGHT_QUALITY)
    - Encourage faster execution via a linear time penalty converted to a 0–100 speed score (WEIGHT_SPEED)
    - Reward thoroughness by crediting key findings (WEIGHT_FINDINGS)
    """
    speed_score = max(
        0.0,
        100.0 - min(execution_time * SPEED_PENALTY_PER_SECOND, 100.0),
    )
    findings_score = len(eda_report.key_findings) * FINDINGS_SCORE_PER_ITEM
    return (
        eda_report.data_quality_score * WEIGHT_QUALITY
        + speed_score * WEIGHT_SPEED
        + findings_score * WEIGHT_FINDINGS
    )


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
            user_prompt = build_user_prompt(main_ref, dataset_df)
            result = agent.run_sync(user_prompt, deps=deps)
            eda_report = result.output

            execution_time = time.time() - start_time

            # Score this variant
            score = compute_prompt_score(eda_report, execution_time)

            results.append(
                {
                    "prompt_id": prompt_id,
                    "prompt": system_prompt,
                    "score": score,
                    "quality_score": eda_report.data_quality_score,
                    "execution_time": execution_time,
                    "findings_count": len(eda_report.key_findings),
                    "success": True,
                }
            )

            logger.info(
                f"✅ {prompt_id}: score={score:.1f}, time={execution_time:.1f}s"
            )

        except Exception as e:
            logger.warning(f"❌ {prompt_id} failed: {e}")
            results.append(
                {
                    "prompt_id": prompt_id,
                    "prompt": system_prompt,
                    "score": 0,
                    "success": False,
                    "error": str(e),
                }
            )

    # Find best performer
    successful_results = [r for r in results if r["success"]]

    if not successful_results:
        logger.warning(
            "All prompts failed, falling back to DEFAULT_SYSTEM_PROMPT"
        )
        best_prompt = DEFAULT_SYSTEM_PROMPT
    else:
        best_result = max(successful_results, key=lambda x: x["score"])
        best_prompt = best_result["prompt"]
        logger.info(
            f"🏆 Best prompt: {best_result['prompt_id']} (score: {best_result['score']:.1f})"
        )

    logger.info("💾 Best prompt will be stored with exclusive 'optimized' tag")

    # Add exclusive tag to this step's output artifact
    add_tags(tags=[Tag(name="optimized", exclusive=True)], infer_artifact=True)

    return best_prompt


def get_optimized_prompt() -> str:
    """Retrieve the optimized prompt using ZenML's tag-based filtering.

    This demonstrates ZenML's tag filtering by finding artifacts tagged with 'optimized'.
    Since 'optimized' is an exclusive tag, there will be at most one such artifact.

    Returns:
        The optimized prompt from the latest optimization run as a plain string,
        or DEFAULT_SYSTEM_PROMPT if none found or retrieval fails.
    """
    try:
        client = Client()

        # Find artifacts tagged with 'optimized' (our exclusive tag)
        artifacts = client.list_artifact_versions(tags=["optimized"], size=1)

        if artifacts.items:
            optimized_artifact = artifacts.items[0]
            prompt_value = optimized_artifact.load()
            logger.info(
                f"🎯 Retrieved optimized prompt from artifact: {optimized_artifact.id}"
            )
            logger.info(f"   Artifact created: {optimized_artifact.created}")
            return prompt_value
        else:
            logger.info(
                "🔍 No optimized prompt found (no artifacts with 'optimized' tag). Using DEFAULT_SYSTEM_PROMPT."
            )

    except Exception as e:
        logger.warning(
            f"Failed to retrieve optimized prompt: {e}. Falling back to DEFAULT_SYSTEM_PROMPT."
        )

    # Fallback to default system prompt if no optimization artifacts found or retrieval failed
    logger.info(
        "📝 Using default system prompt (run optimization pipeline first)"
    )
    return DEFAULT_SYSTEM_PROMPT
