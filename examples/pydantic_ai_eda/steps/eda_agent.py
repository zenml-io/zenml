"""Simple EDA agent step using Pydantic AI."""

from typing import Annotated, Any, Dict, List, Tuple

import pandas as pd
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from zenml import step
from zenml.types import MarkdownString

# Logfire for observability
try:
    import logfire

    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False

from models import AgentConfig, EDAReport
from steps.agent_tools import AGENT_TOOLS, AnalystAgentDeps


@step
def run_eda_agent(
    dataset_df: pd.DataFrame,
    dataset_metadata: Dict[str, Any],
    agent_config: AgentConfig = None,
) -> Tuple[
    Annotated[MarkdownString, "eda_report_markdown"],
    Annotated[Dict[str, Any], "eda_report_json"],
    Annotated[List[Dict[str, str]], "sql_execution_log"],
    Annotated[Dict[str, pd.DataFrame], "analysis_tables"],
]:
    """Run simple Pydantic AI agent for EDA analysis."""
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

    # Initialize agent dependencies and store the dataset
    deps = AnalystAgentDeps()
    main_ref = deps.store(dataset_df)

    # Create the EDA analyst agent with focused system prompt
    system_prompt = """You are a data analyst. Perform quick but insightful EDA.

FOCUS ON:
- Data quality score (0-100) based on missing data and duplicates
- Key patterns and distributions
- Notable correlations or anomalies
- 2-3 actionable recommendations

Be concise but specific with numbers. Aim for quality insights, not exhaustive analysis."""

    analyst_agent = Agent(
        f"openai:{agent_config.model_name}",
        deps_type=AnalystAgentDeps,
        output_type=EDAReport,
        output_retries=3,  # Allow more retries for result validation
        system_prompt=system_prompt,
        model_settings=ModelSettings(
            parallel_tool_calls=True,
        ),
    )

    # Register tools
    for tool in AGENT_TOOLS:
        analyst_agent.tool(tool)

    # Run focused analysis
    user_prompt = f"""Quick EDA analysis for dataset '{main_ref}' ({dataset_df.shape[0]} rows, {dataset_df.shape[1]} cols).

STEPS (keep it fast):
1. display('{main_ref}') - check data structure  
2. describe('{main_ref}') - get key stats
3. run_sql('{main_ref}', 'SELECT COUNT(*) as total, COUNT(DISTINCT *) as unique FROM dataset') - check duplicates
4. If multiple numeric columns: analyze_correlations('{main_ref}')

Generate EDAReport with data quality score and 2-3 key insights."""

    try:
        result = analyst_agent.run_sync(user_prompt, deps=deps)
        eda_report = result.output
    except Exception as e:
        # Simple fallback - create basic report
        eda_report = EDAReport(
            headline=f"Basic analysis of {dataset_df.shape[0]} rows, {dataset_df.shape[1]} columns",
            key_findings=[
                f"Dataset contains {len(dataset_df)} rows and {len(dataset_df.columns)} columns"
            ],
            risks=["Analysis failed - using basic fallback"],
            fixes=[],
            data_quality_score=50.0,
            markdown=f"# EDA Report\n\nBasic analysis failed: {str(e)}\n\nDataset shape: {dataset_df.shape}",
            column_profiles={},
            correlation_insights=[],
            missing_data_analysis={},
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
                "tool_calls": len(deps.query_history),
            },
        },
        deps.query_history,
        {
            ref: df
            for ref, df in deps.output.items()
            if ref != main_ref and len(df) <= 1000
        },
    )
