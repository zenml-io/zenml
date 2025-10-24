"""Simple EDA agent step using Pydantic AI."""

from typing import Annotated, Any, Dict, List, Tuple

import pandas as pd
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from zenml import step
from zenml.logger import get_logger
from zenml.types import MarkdownString

logger = get_logger(__name__)


# Logfire for observability
try:
    import logfire

    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False

from models import AgentConfig, EDAReport
from steps.agent_tools import AGENT_TOOLS, AnalystAgentDeps, budget_wrapper
from steps.prompt_text import DEFAULT_SYSTEM_PROMPT, build_user_prompt


@step
def run_eda_agent(
    dataset_df: pd.DataFrame,
    dataset_metadata: Dict[str, Any],
    agent_config: AgentConfig = None,
    custom_system_prompt: str = None,
) -> Tuple[
    Annotated[MarkdownString, "eda_report_markdown"],
    Annotated[Dict[str, Any], "eda_report_json"],
    Annotated[List[Dict[str, Any]], "sql_execution_log"],
    Annotated[Dict[str, pd.DataFrame], "analysis_tables"],
]:
    """Run Pydantic AI agent for EDA analysis with optional custom prompt.

    Args:
        dataset_df: Dataset to analyze
        dataset_metadata: Metadata about the dataset
        agent_config: Configuration for the AI agent
        custom_system_prompt: Optional custom system prompt (overrides default)

    Returns:
        Tuple of EDA outputs: markdown report, JSON report, SQL log, analysis tables
    """
    if agent_config is None:
        agent_config = AgentConfig()

    # Configure Logfire for observability
    if LOGFIRE_AVAILABLE:
        try:
            logfire.configure()
            logfire.instrument_pydantic_ai()
            logfire.info("EDA agent starting", dataset_shape=dataset_df.shape)
        except Exception as e:
            print(f"Warning: Failed to configure Logfire: {e}")

    # Initialize agent dependencies with time budget and store the dataset
    deps = AnalystAgentDeps(
        time_budget_s=float(agent_config.timeout_seconds)
        if agent_config
        else None
    )
    main_ref = deps.store(dataset_df)

    # Create the EDA analyst agent with system prompt (custom or default)
    if custom_system_prompt:
        system_prompt = custom_system_prompt
        logger.info("🎯 Using custom optimized system prompt for analysis")
    else:
        system_prompt = DEFAULT_SYSTEM_PROMPT
        logger.info("📝 Using default system prompt for analysis")

    # Provider:model id computed once for both agent creation and metadata
    provider_model = agent_config.model_id()

    analyst_agent = Agent(
        provider_model,
        deps_type=AnalystAgentDeps,
        output_type=EDAReport,
        output_retries=3,  # Allow more retries for result validation
        system_prompt=system_prompt,
        model_settings=ModelSettings(
            parallel_tool_calls=True,
        ),
    )

    # Use shared budget wrapper to enforce time/tool-call limits for all tools
    wrapper = budget_wrapper(getattr(agent_config, "max_tool_calls", None))

    # Register tools with budget enforcement
    for tool in AGENT_TOOLS:
        analyst_agent.tool(wrapper(tool))

    # Run focused analysis using shared user prompt builder
    user_prompt = build_user_prompt(main_ref, dataset_df)

    try:
        result = analyst_agent.run_sync(user_prompt, deps=deps)
        eda_report = result.output
    except Exception as e:
        eda_report = EDAReport(
            headline=f"Analysis failed for dataset with {dataset_df.shape[0]} rows",
            key_findings=[
                f"Dataset contains {len(dataset_df)} rows and {len(dataset_df.columns)} columns.",
                "The AI agent failed to generate a report.",
            ],
            data_quality_score=0.0,
            markdown=(
                f"# EDA Report Failed\n\n"
                f"Analysis failed with error: {str(e)}\n\n"
                f"Dataset shape: {dataset_df.shape}"
            ),
        )

    # Return results
    return (
        MarkdownString(eda_report.markdown),
        {
            "headline": eda_report.headline,
            "key_findings": eda_report.key_findings,
            "data_quality_score": eda_report.data_quality_score,
            "agent_metadata": {
                "model": agent_config.model_name,
                "provider_model": provider_model,
                "tool_calls": deps.tool_calls,
                "sql_queries": len(deps.query_history),
            },
        },
        deps.query_history,
        {
            ref: df
            for ref, df in deps.output.items()
            if ref != main_ref and len(df) <= 1000
        },
    )
