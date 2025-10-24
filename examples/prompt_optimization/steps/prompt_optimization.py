"""Simple prompt optimization step for demonstrating ZenML artifact management."""

import time
from typing import Annotated, List, Optional, Tuple

import pandas as pd
from models import AgentConfig, EDAReport, ScoringConfig, VariantScore
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from steps.agent_tools import AGENT_TOOLS, AnalystAgentDeps, budget_wrapper
from steps.prompt_text import DEFAULT_SYSTEM_PROMPT, build_user_prompt

from zenml import ArtifactConfig, Tag, add_tags, step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


# NOTE: Quality and speed are both on a 0–100 scale. Findings accrue raw points
# (capped via `findings_cap`) before weights are applied. After weight normalization,
# the aggregate score remains roughly bounded within 0–100.
def compute_prompt_score(
    eda_report: EDAReport, execution_time: float, scoring: ScoringConfig
) -> float:
    wq, ws, wf = scoring.normalized_weights
    speed_penalty = min(
        execution_time * scoring.speed_penalty_per_second, 100.0
    )
    speed_score = max(0.0, 100.0 - speed_penalty)
    credited_findings = min(len(eda_report.key_findings), scoring.findings_cap)
    findings_score = credited_findings * scoring.findings_score_per_item
    return (
        eda_report.data_quality_score * wq
        + speed_score * ws
        + findings_score * wf
    )


@step
def compare_prompts_and_tag_best(
    dataset_df: pd.DataFrame,
    prompt_variants: List[str],
    agent_config: AgentConfig | None = None,
    scoring_config: Optional[ScoringConfig] = None,
) -> Tuple[
    Annotated[str, ArtifactConfig(name="best_prompt")],
    Annotated[List[VariantScore], ArtifactConfig(name="prompt_scoreboard")],
]:
    """Compare prompt variants, compute scores, and emit best prompt + scoreboard.

    Behavior:
    - Provider/model inference owned by AgentConfig.model_id()
    - Uniform time/tool-call budget enforcement via tool wrappers
    - Score each variant using ScoringConfig; record success/failure with timing
    - Tag best prompt with exclusive 'optimized' tag only if at least one success

    Args:
        dataset_df: Dataset to test prompts against
        prompt_variants: List of system prompts to compare
        agent_config: Configuration for AI agents (defaults applied if None)
        scoring_config: Scoring configuration (defaults applied if None)

    Returns:
        Tuple of:
        - Best performing prompt string (artifact name 'best_prompt')
        - Scoreboard entries for all variants (artifact name 'prompt_scoreboard')
    """
    if agent_config is None:
        agent_config = AgentConfig()
    if scoring_config is None:
        scoring_config = ScoringConfig()

    logger.info(f"🧪 Testing {len(prompt_variants)} prompt variants")

    # Compute provider:model id once for consistent use across variants
    provider_model = agent_config.model_id()

    # Prepare a shared wrapper that enforces budgets for all tools
    wrapper = budget_wrapper(getattr(agent_config, "max_tool_calls", None))

    # Collect VariantScore entries for all variants (success and failure)
    scoreboard: List[VariantScore] = []

    for i, system_prompt in enumerate(prompt_variants):
        prompt_id = f"variant_{i + 1}"
        logger.info(f"Testing {prompt_id}...")

        start_time = time.time()

        try:
            # Create agent with this prompt and per-variant deps with time budget
            deps = AnalystAgentDeps(
                time_budget_s=float(agent_config.timeout_seconds)
                if agent_config
                else None
            )
            deps.tool_calls = (
                0  # Ensure tool-call counter is reset per variant
            )
            main_ref = deps.store(dataset_df)

            agent = Agent(
                provider_model,
                deps_type=AnalystAgentDeps,
                output_type=EDAReport,
                system_prompt=system_prompt,
                model_settings=ModelSettings(parallel_tool_calls=False),
            )

            # Register tools with shared budget enforcement
            for tool in AGENT_TOOLS:
                agent.tool(wrapper(tool))

            # Run analysis
            user_prompt = build_user_prompt(main_ref, dataset_df)
            result = agent.run_sync(user_prompt, deps=deps)
            eda_report = result.output

            execution_time = time.time() - start_time

            # Score this variant using provided scoring configuration
            score = compute_prompt_score(
                eda_report, execution_time, scoring_config
            )

            scoreboard.append(
                VariantScore(
                    prompt_id=prompt_id,
                    prompt=system_prompt,
                    score=score,
                    quality_score=eda_report.data_quality_score,
                    execution_time=execution_time,
                    findings_count=len(eda_report.key_findings),
                    success=True,
                    error=None,
                )
            )

            logger.info(
                f"✅ {prompt_id}: score={score:.1f}, time={execution_time:.1f}s"
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.warning(f"❌ {prompt_id} failed: {e}")
            scoreboard.append(
                VariantScore(
                    prompt_id=prompt_id,
                    prompt=system_prompt,
                    score=0.0,
                    quality_score=0.0,
                    execution_time=execution_time,
                    findings_count=0,
                    success=False,
                    error=str(e),
                )
            )

    # Determine best performer among successful variants
    successful_results = [entry for entry in scoreboard if entry.success]

    if not successful_results:
        logger.warning(
            "All prompts failed, falling back to DEFAULT_SYSTEM_PROMPT"
        )
        best_prompt = DEFAULT_SYSTEM_PROMPT
        logger.info("⏭️ Skipping best prompt tagging since all variants failed")
    else:
        best_result = max(successful_results, key=lambda x: x.score)
        best_prompt = best_result.prompt
        logger.info(
            f"🏆 Best prompt: {best_result.prompt_id} (score: {best_result.score:.1f})"
        )

        logger.info(
            "💾 Best prompt will be stored with exclusive 'optimized' tag"
        )
        # Explicitly target the named output artifact to avoid multi-output ambiguity
        add_tags(
            tags=[Tag(name="optimized", exclusive=True)],
            output_name="best_prompt",
        )

    return best_prompt, scoreboard


def get_optimized_prompt() -> Tuple[str, bool]:
    """Retrieve the optimized prompt from a tagged artifact, with safe fallback.

    This demonstrates ZenML's tag filtering by finding artifacts tagged with 'optimized'.
    Since 'optimized' is an exclusive tag, there will be at most one such artifact.

    Returns:
        Tuple[str, bool]: (prompt, from_artifact) where:
          - prompt: The optimized prompt text if found; DEFAULT_SYSTEM_PROMPT otherwise.
          - from_artifact: True if the prompt was retrieved from an artifact; False on fallback.
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
            return prompt_value, True
        else:
            logger.info(
                "🔍 No optimized prompt found (no artifacts with 'optimized' tag). "
                "Falling back to default (from_artifact=False)."
            )

    except Exception as e:
        logger.warning(
            f"Failed to retrieve optimized prompt: {e}. Falling back to DEFAULT_SYSTEM_PROMPT (from_artifact=False)."
        )

    # Fallback to default system prompt if lookup fails
    logger.info(
        "📝 Using default system prompt (run optimization pipeline first). from_artifact=False"
    )
    return DEFAULT_SYSTEM_PROMPT, False
