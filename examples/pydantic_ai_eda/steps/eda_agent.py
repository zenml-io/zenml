"""EDA agent step using Pydantic AI for automated data analysis.

This step implements the core EDA agent that uses Pydantic AI to perform
intelligent exploratory data analysis through SQL queries and structured reporting.
"""

import logging
import time
from typing import Annotated, Any, Dict, List, Tuple

import pandas as pd

from zenml import log_metadata, step
from zenml.types import MarkdownString

# Logfire for observability
try:
    import logfire

    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False

from models import AgentConfig, DataQualityFix, EDAReport
from steps.agent_tools import AGENT_TOOLS, AnalystAgentDeps

logger = logging.getLogger(__name__)

# (HTML visualization removed as per simplification decision)


# EDA analysis prompt template
EDA_SYSTEM_PROMPT = """You are an expert data analyst. Your task is to perform a focused exploratory data analysis (EDA) and produce a final EDAReport within 15 tool calls maximum.

## CRITICAL: Follow this exact workflow:
1. **Initial Assessment** (2-3 tool calls):
   - display('dataset') to see the data structure  
   - profile('dataset') for basic statistics
   - run_duckdb('dataset', 'SELECT COUNT(*), COUNT(DISTINCT *) as unique_rows FROM dataset') for size/duplicates

2. **Data Quality Analysis** (3-4 tool calls):
   - Check missing data: SELECT column_name, COUNT(*) - COUNT(column_name) as nulls FROM (SELECT * FROM dataset LIMIT 1) CROSS JOIN (SELECT column_name FROM information_schema.columns WHERE table_name = 'dataset')
   - Identify duplicates if any found in step 1
   - Check for obvious outliers in numeric columns (use percentiles)

3. **Key Insights** (2-3 tool calls):
   - Calculate correlations between numeric columns if >1 numeric column exists
   - Analyze categorical distributions for top categories
   - Identify most important patterns or issues

4. **STOP and Generate Report** (1 tool call):
   - Produce the final EDAReport with all required fields
   - Do NOT continue exploring after generating the report

## Available Tools:
- run_duckdb(dataset_ref, sql): Execute SQL against 'dataset' table (read-only)
- display(dataset_ref): Show first 10 rows
- profile(dataset_ref): Get statistical summary
- save_csv(dataset_ref, filename): Save query results

## SQL Guidelines:
- Table name is 'dataset'
- Use efficient aggregations, avoid SELECT *
- Limit large result sets with LIMIT clause
- Focus on summary statistics, not raw data exploration

## REQUIRED Output Format:
You MUST produce an EDAReport with:
- headline: Executive summary (1 sentence)
- key_findings: 3-5 critical discoveries
- risks: Data quality issues found
- fixes: Specific DataQualityFix objects for issues
- data_quality_score: 0-100 score based on:
  * Missing data: 0-15%=good(30pts), 16-30%=fair(20pts), >30%=poor(10pts)
  * Duplicates: 0-5%=good(25pts), 6-15%=fair(15pts), >15%=poor(5pts)  
  * Schema quality: All columns have data=good(25pts), some empty=fair(15pts)
  * Consistency: Clean data=good(20pts), issues found=poor(10pts)
- markdown: Summary report for humans
- column_profiles: Per-column statistics from profiling
- correlation_insights: Key relationships found
- missing_data_analysis: Missing data summary

## EFFICIENCY RULES:
- Maximum 15 tool calls total
- Stop analysis once you have enough information for the report
- Focus on critical issues, not exhaustive exploration  
- Generate the final report as soon as you have sufficient insights
- Do NOT keep exploring after finding basic patterns"""


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
    """Run Pydantic AI agent for EDA analysis.

    Executes an AI agent that performs comprehensive exploratory data analysis
    on the provided dataset using SQL queries and statistical analysis.

    Args:
        dataset_df: The dataset to analyze
        dataset_metadata: Metadata about the dataset
        agent_config: Configuration for agent behavior

    Returns:
        Tuple of (report_markdown, report_json, sql_log, analysis_tables)
        containing all artifacts generated during the EDA analysis
    """
    start_time = time.time()

    # Configure Logfire with explicit token
    if LOGFIRE_AVAILABLE:
        try:
            logfire.configure()
            logfire.instrument_pydantic_ai()
            logfire.info("EDA agent starting", dataset_shape=dataset_df.shape)
        except Exception as e:
            logger.warning(f"Failed to configure Logfire: {e}")

    if agent_config is None:
        agent_config = AgentConfig()

    logger.info(f"Starting EDA analysis with {agent_config.model_name}")
    logger.info(f"Dataset shape: {dataset_df.shape}")

    try:
        # Initialize agent dependencies
        deps = AnalystAgentDeps()

        # Store the main dataset as Out[1]
        main_ref = deps.store_dataset(dataset_df, "Out[1]")
        logger.info(f"Stored main dataset as {main_ref}")

        # Initialize and run the Pydantic AI agent
        try:
            import asyncio

            import nest_asyncio
            from pydantic_ai import Agent
            from pydantic_ai.models.anthropic import AnthropicModel
            from pydantic_ai.models.openai import OpenAIModel

            # Select model based on configuration
            if agent_config.model_name.startswith("gpt"):
                model = OpenAIModel(agent_config.model_name)
            elif agent_config.model_name.startswith("claude"):
                model = AnthropicModel(agent_config.model_name)
            else:
                # Default to OpenAI
                model = OpenAIModel("gpt-5")
                logger.warning(
                    f"Unknown model {agent_config.model_name}, defaulting to gpt-5"
                )

            # Create the agent with tools and stricter limits
            agent = Agent(
                model=model,
                system_prompt=EDA_SYSTEM_PROMPT,
                deps_type=AnalystAgentDeps,
                result_type=EDAReport,
            )

            # Set strict tool call limits
            if hasattr(agent, "max_tool_calls"):
                agent.max_tool_calls = 15
            elif hasattr(agent, "_max_tool_calls"):
                agent._max_tool_calls = 15

            # Register tools
            for tool_func in AGENT_TOOLS.values():
                agent.tool(tool_func)

            # Prepare initial context with clear instructions
            initial_prompt = f"""ANALYZE THIS DATASET EFFICIENTLY - Maximum 15 tool calls.

Dataset Information:
- Shape: {dataset_df.shape}
- Columns: {list(dataset_df.columns)}  
- Source: {dataset_metadata.get("source_type", "unknown")}

WORKFLOW (stick to this exactly):
1. display('dataset') - see the data
2. profile('dataset') - get basic stats  
3. run_duckdb('dataset', 'SELECT COUNT(*), COUNT(DISTINCT *) FROM dataset') - check duplicates
4. Check missing data patterns with SQL
5. Analyze key relationships/distributions (max 3 queries)
6. STOP and generate final EDAReport

Do NOT over-analyze. Focus on critical issues only. Generate your report once you have the essential insights."""

            # Run the agent with timeout
            try:

                async def run_agent():
                    result = await agent.run(initial_prompt, deps=deps)
                    return result

                # Run with timeout
                result = asyncio.wait_for(
                    run_agent(), timeout=agent_config.timeout_seconds
                )

                # If we're in a sync context, run it
                try:
                    result = asyncio.run(result)
                except RuntimeError:
                    # Already in an event loop
                    nest_asyncio.apply()
                    result = asyncio.run(result)

            except ImportError:
                # Fallback to mock analysis if pydantic-ai not available
                logger.warning(
                    "Pydantic AI not available, running fallback analysis"
                )
                result = _run_fallback_analysis(dataset_df, deps)

        except ImportError:
            logger.warning(
                "Pydantic AI not available, running fallback analysis"
            )
            result = _run_fallback_analysis(dataset_df, deps)

        # Extract results
        if hasattr(result, "data"):
            eda_report = result.data
        else:
            eda_report = result

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Prepare return artifacts
        report_markdown = eda_report.markdown

        report_json = {
            "headline": eda_report.headline,
            "key_findings": eda_report.key_findings,
            "risks": eda_report.risks,
            "fixes": [fix.model_dump() for fix in eda_report.fixes],
            "data_quality_score": eda_report.data_quality_score,
            "column_profiles": eda_report.column_profiles,
            "correlation_insights": eda_report.correlation_insights,
            "missing_data_analysis": eda_report.missing_data_analysis,
            "processing_time_ms": processing_time_ms,
            "agent_metadata": {
                "model": agent_config.model_name,
                "tool_calls": len(deps.query_history),
                "datasets_created": len(deps.datasets),
            },
        }

        # Get SQL execution log
        sql_log = deps.query_history.copy()

        # Filter analysis tables (keep only reasonably sized ones)
        analysis_tables = {}
        for ref, df in deps.datasets.items():
            if (
                ref != "Out[1]" and len(df) <= 10000
            ):  # Don't return huge tables
                analysis_tables[ref] = df

        logger.info(f"EDA analysis completed in {processing_time_ms}ms")
        logger.info(f"Generated {len(analysis_tables)} analysis tables")
        logger.info(f"Data quality score: {eda_report.data_quality_score}")

        # Log enhanced metadata for ZenML dashboard
        _log_agent_metadata(
            agent_config=agent_config,
            eda_report=eda_report,
            processing_time_ms=processing_time_ms,
            sql_log=sql_log,
            analysis_tables=analysis_tables,
            result=result if "result" in locals() else None,
        )

        # Determine tool names dynamically when possible
        tool_names: List[str] = list(AGENT_TOOLS.keys())
        try:
            if "agent" in locals():
                tools_attr = getattr(agent, "tools", None)
                if tools_attr is None:
                    tools_attr = getattr(agent, "_tools", None)
                if tools_attr is not None:
                    if isinstance(tools_attr, dict):
                        tool_names = list(tools_attr.keys())
                    else:
                        possible_keys = getattr(tools_attr, "keys", None)
                        if callable(possible_keys):
                            tool_names = list(possible_keys())
        except Exception:
            # Best-effort fallback
            pass

        # Convert markdown to MarkdownString for proper rendering
        markdown_artifact = MarkdownString(report_markdown)

        return markdown_artifact, report_json, sql_log, analysis_tables

    except Exception as e:
        logger.error(f"EDA agent failed: {e}")

        # Run fallback analysis to preserve any existing context and generate basic results
        logger.info("Running fallback analysis after agent failure")
        fallback_report = _run_fallback_analysis(dataset_df, deps)
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Prepare return artifacts with fallback data
        report_markdown = (
            fallback_report.markdown
            + f"\n\n**Note:** Analysis completed in fallback mode after agent error: {str(e)}"
        )

        report_json = {
            "headline": f"EDA analysis completed (fallback mode after error: {str(e)})",
            "key_findings": fallback_report.key_findings,
            "risks": fallback_report.risks
            + [f"Original agent failed: {str(e)}"],
            "fixes": [fix.model_dump() for fix in fallback_report.fixes],
            "data_quality_score": fallback_report.data_quality_score,
            "column_profiles": fallback_report.column_profiles,
            "correlation_insights": fallback_report.correlation_insights,
            "missing_data_analysis": fallback_report.missing_data_analysis,
            "processing_time_ms": processing_time_ms,
            "agent_metadata": {
                "model": "fallback_after_error",
                "tool_calls": len(deps.query_history),
                "datasets_created": len(deps.datasets),
                "error": str(e),
            },
        }

        # Get SQL execution log (preserving any queries that were executed before failure)
        sql_log = deps.query_history.copy()

        # Filter analysis tables (preserving any tables created before failure)
        analysis_tables = {}
        for ref, df in deps.datasets.items():
            if ref != "Out[1]" and ref != "main_dataset" and len(df) <= 10000:
                analysis_tables[ref] = df

        # Convert markdown to MarkdownString
        error_markdown_artifact = MarkdownString(report_markdown)

        logger.info(
            f"Fallback analysis preserved {len(sql_log)} SQL queries and {len(analysis_tables)} analysis tables"
        )

        # Log error metadata
        log_metadata(
            {
                "ai_agent_execution": {
                    "model_name": agent_config.model_name
                    if agent_config
                    else "unknown",
                    "processing_time_ms": processing_time_ms,
                    "success": False,
                    "error_message": str(e),
                    "tool_calls_made": len(sql_log),
                    "datasets_created": len(analysis_tables),
                    "fallback_mode": True,
                },
                "data_quality_assessment": {
                    "quality_score": fallback_report.data_quality_score,
                    "issues_found": len(fallback_report.fixes),
                    "risk_count": len(fallback_report.risks),
                    "key_findings_count": len(fallback_report.key_findings),
                },
            }
        )

        return (
            error_markdown_artifact,
            report_json,
            sql_log,
            analysis_tables,
        )


def _run_fallback_analysis(
    dataset_df: pd.DataFrame, deps: AnalystAgentDeps
) -> EDAReport:
    """Fallback analysis when Pydantic AI is not available.

    Performs basic statistical analysis and generates a simple report
    using pandas operations instead of AI-driven analysis. Also simulates
    some SQL queries to populate logs and analysis tables.
    """
    logger.info("Running fallback EDA analysis")

    # Store the main dataset
    deps.store_dataset(dataset_df, "main_dataset")

    # Run some basic SQL-like analysis to populate logs and tables
    _run_fallback_sql_analysis(dataset_df, deps)

    # Basic statistics
    numeric_cols = dataset_df.select_dtypes(
        include=["number"]
    ).columns.tolist()
    categorical_cols = dataset_df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    # Calculate missing data
    missing_counts = dataset_df.isnull().sum()
    missing_pct = (missing_counts / len(dataset_df) * 100).round(2)

    # Calculate quality score
    quality_factors = []

    # Missing data factor (0-40 points)
    overall_missing_pct = (
        dataset_df.isnull().sum().sum()
        / (len(dataset_df) * len(dataset_df.columns))
        * 100
    )
    if overall_missing_pct <= 5:
        quality_factors.append(40)
    elif overall_missing_pct <= 15:
        quality_factors.append(30)
    elif overall_missing_pct <= 30:
        quality_factors.append(20)
    else:
        quality_factors.append(10)

    # Duplicate factor (0-30 points)
    duplicate_count = dataset_df.duplicated().sum()
    duplicate_pct = duplicate_count / len(dataset_df) * 100
    if duplicate_pct <= 1:
        quality_factors.append(30)
    elif duplicate_pct <= 5:
        quality_factors.append(25)
    elif duplicate_pct <= 15:
        quality_factors.append(15)
    else:
        quality_factors.append(5)

    # Schema completeness factor (0-30 points)
    if len(dataset_df.columns) > 0:
        non_empty_cols = (dataset_df.notna().any()).sum()
        schema_completeness = non_empty_cols / len(dataset_df.columns) * 30
        quality_factors.append(int(schema_completeness))
    else:
        quality_factors.append(0)

    data_quality_score = sum(quality_factors)

    # Generate key findings
    key_findings = []
    key_findings.append(
        f"Dataset contains {len(dataset_df):,} rows and {len(dataset_df.columns)} columns"
    )

    if numeric_cols:
        key_findings.append(
            f"Found {len(numeric_cols)} numeric columns for quantitative analysis"
        )

    if categorical_cols:
        key_findings.append(
            f"Found {len(categorical_cols)} categorical columns for segmentation analysis"
        )

    if overall_missing_pct > 10:
        key_findings.append(
            f"Missing data is {overall_missing_pct:.1f}% overall, requiring attention"
        )

    if duplicate_count > 0:
        key_findings.append(
            f"Found {duplicate_count:,} duplicate rows ({duplicate_pct:.1f}%)"
        )

    # Generate risks
    risks = []
    if overall_missing_pct > 20:
        risks.append(
            "High percentage of missing data may impact analysis quality"
        )

    if duplicate_pct > 10:
        risks.append(
            "Significant duplicate data may skew statistical analysis"
        )

    if len(numeric_cols) == 0:
        risks.append("No numeric columns found for quantitative analysis")

    # Generate fixes
    fixes = []

    high_missing_cols = missing_pct[missing_pct > 30].index.tolist()
    if high_missing_cols:
        fixes.append(
            DataQualityFix(
                title="Address high missing data in key columns",
                rationale=f"Columns {high_missing_cols} have >30% missing values",
                severity="high",
                code_snippet="df.dropna(subset=['high_missing_col']) or df.fillna(method='forward')",
                affected_columns=high_missing_cols,
                estimated_impact=0.3,
            )
        )

    if duplicate_count > 0:
        fixes.append(
            DataQualityFix(
                title="Remove duplicate records",
                rationale=f"Found {duplicate_count:,} duplicate rows affecting data integrity",
                severity="medium" if duplicate_pct < 10 else "high",
                code_snippet="df.drop_duplicates(inplace=True)",
                affected_columns=list(dataset_df.columns),
                estimated_impact=duplicate_pct / 100,
            )
        )

    # Column profiles
    column_profiles = {}
    for col in dataset_df.columns:
        profile = {
            "dtype": str(dataset_df[col].dtype),
            "null_count": int(missing_counts[col]),
            "null_percentage": float(missing_pct[col]),
            "unique_count": int(dataset_df[col].nunique()),
        }

        if col in numeric_cols and dataset_df[col].notna().sum() > 0:
            profile.update(
                {
                    "mean": float(dataset_df[col].mean()),
                    "std": float(dataset_df[col].std()),
                    "min": float(dataset_df[col].min()),
                    "max": float(dataset_df[col].max()),
                    "median": float(dataset_df[col].median()),
                }
            )
        elif col in categorical_cols and dataset_df[col].notna().sum() > 0:
            value_counts = dataset_df[col].value_counts().head(5)
            profile["top_values"] = value_counts.to_dict()

        column_profiles[col] = profile

    # Correlation insights
    correlation_insights = []
    if len(numeric_cols) > 1:
        corr_matrix = dataset_df[numeric_cols].corr()
        high_corrs = []
        for i, col1 in enumerate(numeric_cols):
            for j, col2 in enumerate(numeric_cols[i + 1 :], i + 1):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    high_corrs.append((col1, col2, corr_val))

        if high_corrs:
            correlation_insights.append(
                f"Found {len(high_corrs)} high correlations (>0.7)"
            )
            for col1, col2, corr in high_corrs[:3]:  # Show top 3
                correlation_insights.append(
                    f"{col1} and {col2} are strongly correlated ({corr:.3f})"
                )
        else:
            correlation_insights.append(
                "No strong correlations (>0.7) detected between numeric variables"
            )

    # Missing data analysis
    missing_data_analysis = {
        "total_missing_cells": int(missing_counts.sum()),
        "missing_percentage": float(overall_missing_pct),
        "columns_with_missing": missing_counts[missing_counts > 0].to_dict(),
        "completely_missing_columns": missing_counts[
            missing_counts == len(dataset_df)
        ].index.tolist(),
    }

    # Generate markdown report
    markdown_report = f"""# EDA Report (Fallback Analysis)

## Executive Summary
{key_findings[0] if key_findings else "Basic dataset analysis completed"}

**Data Quality Score: {data_quality_score}/100**

## Key Findings
{chr(10).join(f"- {finding}" for finding in key_findings)}

## Data Quality Issues
{chr(10).join(f"- {risk}" for risk in risks) if risks else "No major quality issues detected"}

## Column Overview
| Column | Type | Missing | Unique |
|--------|------|---------|--------|
{chr(10).join(f"| {col} | {profile['dtype']} | {profile['null_percentage']:.1f}% | {profile['unique_count']} |" for col, profile in column_profiles.items())}

## Recommendations
{chr(10).join(f"- {fix.title}: {fix.rationale}" for fix in fixes) if fixes else "- Dataset appears to be in good condition"}

*Report generated by ZenML EDA Pipeline (fallback mode)*
"""

    return EDAReport(
        headline=key_findings[0]
        if key_findings
        else "Basic EDA analysis completed",
        key_findings=key_findings,
        risks=risks,
        fixes=fixes,
        data_quality_score=data_quality_score,
        markdown=markdown_report,
        column_profiles=column_profiles,
        correlation_insights=correlation_insights,
        missing_data_analysis=missing_data_analysis,
    )


def _run_fallback_sql_analysis(
    dataset_df: pd.DataFrame, deps: AnalystAgentDeps
):
    """Run basic SQL-like analysis to populate logs and analysis tables for fallback mode."""
    import time

    import duckdb

    try:
        # Create DuckDB connection
        conn = duckdb.connect(":memory:")
        conn.register("dataset", dataset_df)

        # Run some basic SQL queries to simulate what the AI agent would do
        fallback_queries = [
            ("SELECT COUNT(*) as row_count FROM dataset", "basic_stats"),
            (
                "SELECT COUNT(*) as col_count FROM (SELECT * FROM dataset LIMIT 1)",
                "column_count",
            ),
        ]

        # Add column-specific queries
        for col in dataset_df.columns[:5]:  # Limit to first 5 columns
            # Escape column names with spaces
            escaped_col = f'"{col}"' if " " in col else col

            # Count nulls
            fallback_queries.append(
                (
                    f"SELECT COUNT(*) - COUNT({escaped_col}) as null_count FROM dataset",
                    f"nulls_{col.replace(' ', '_')}",
                )
            )

            # Get unique counts for non-numeric columns
            if dataset_df[col].dtype == "object" or dataset_df[
                col
            ].dtype.name.startswith("str"):
                fallback_queries.append(
                    (
                        f"SELECT COUNT(DISTINCT {escaped_col}) as unique_count FROM dataset WHERE {escaped_col} IS NOT NULL",
                        f"unique_{col.replace(' ', '_')}",
                    )
                )
            else:
                # Basic stats for numeric columns
                fallback_queries.append(
                    (
                        f"SELECT AVG({escaped_col}) as avg_val, MIN({escaped_col}) as min_val, MAX({escaped_col}) as max_val FROM dataset WHERE {escaped_col} IS NOT NULL",
                        f"stats_{col.replace(' ', '_')}",
                    )
                )

        # Execute queries and log them
        for sql, description in fallback_queries:
            try:
                start_time = time.time()
                result_df = conn.execute(sql).fetchdf()
                execution_time = (time.time() - start_time) * 1000

                # Store result table
                result_ref = deps.store_dataset(
                    result_df, f"fallback_{description}"
                )

                # Log the query
                deps.log_query(
                    sql=sql,
                    result_ref=result_ref,
                    rows_returned=len(result_df),
                    execution_time_ms=execution_time,
                )

            except Exception as e:
                logger.warning(f"Fallback query failed: {sql} - {e}")

        conn.close()
        logger.info(
            f"Fallback analysis executed {len(fallback_queries)} SQL queries"
        )

    except Exception as e:
        logger.warning(f"Could not run fallback SQL analysis: {e}")


def _log_agent_metadata(
    agent_config: AgentConfig,
    eda_report: EDAReport,
    processing_time_ms: int,
    sql_log: List[Dict[str, str]],
    analysis_tables: Dict[str, pd.DataFrame],
    result: Any = None,
) -> None:
    """Log enhanced metadata about AI agent execution for ZenML dashboard."""

    # Calculate token usage if available
    token_usage = {}
    cost_estimate = None
    if result and hasattr(result, "usage"):
        token_usage = {
            "input_tokens": getattr(result.usage, "prompt_tokens", 0),
            "output_tokens": getattr(result.usage, "completion_tokens", 0),
            "total_tokens": getattr(result.usage, "total_tokens", 0),
        }
        cost_estimate = _estimate_cost(result.usage, agent_config.model_name)

    # Calculate SQL execution metrics
    sql_metrics = {}
    if sql_log:
        execution_times = [q.get("execution_time_ms", 0) for q in sql_log]
        sql_metrics = {
            "total_queries": len(sql_log),
            "avg_execution_time_ms": sum(execution_times)
            / len(execution_times)
            if execution_times
            else 0,
            "max_execution_time_ms": max(execution_times)
            if execution_times
            else 0,
            "total_rows_processed": sum(
                q.get("rows_returned", 0) for q in sql_log
            ),
            "query_types": _analyze_query_types(sql_log),
        }

    # Analyze data quality issues by severity
    severity_breakdown = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for fix in eda_report.fixes:
        severity = fix.severity.lower()
        if severity in severity_breakdown:
            severity_breakdown[severity] += 1

    # Log metadata to ZenML
    log_metadata(
        {
            "ai_agent_execution": {
                "model_name": agent_config.model_name,
                "processing_time_ms": processing_time_ms,
                "success": True,
                "tool_calls_made": len(sql_log),
                "datasets_created": len(analysis_tables),
            },
            "token_usage": token_usage,
            "cost_estimate_usd": cost_estimate,
            "data_quality_assessment": {
                "quality_score": eda_report.data_quality_score,
                "issues_found": len(eda_report.fixes),
                "severity_breakdown": severity_breakdown,
                "risk_count": len(eda_report.risks),
                "key_findings_count": len(eda_report.key_findings),
            },
            "sql_execution_metrics": sql_metrics,
            "analysis_summary": {
                "headline": eda_report.headline,
                "columns_analyzed": len(eda_report.column_profiles),
                "correlation_insights": len(eda_report.correlation_insights),
                "missing_data_pct": eda_report.missing_data_analysis.get(
                    "missing_percentage", 0
                ),
            },
        }
    )


def _estimate_cost(usage, model_name: str) -> float:
    """Estimate cost based on token usage and model pricing."""
    if not hasattr(usage, "total_tokens") or usage.total_tokens == 0:
        return 0.0

    # Rough pricing estimates (per 1M tokens)
    pricing = {
        "gpt-4": {"input": 30, "output": 60},
        "gpt-4o": {"input": 5, "output": 15},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "claude-3-5-sonnet": {"input": 3, "output": 15},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
    }

    # Find matching pricing
    model_pricing = None
    for model_key, prices in pricing.items():
        if model_key in model_name.lower():
            model_pricing = prices
            break

    if not model_pricing:
        # Default rough estimate
        return usage.total_tokens * 0.00001

    input_cost = (
        getattr(usage, "prompt_tokens", 0) * model_pricing["input"] / 1_000_000
    )
    output_cost = (
        getattr(usage, "completion_tokens", 0)
        * model_pricing["output"]
        / 1_000_000
    )

    return input_cost + output_cost


def _analyze_query_types(sql_log: List[Dict[str, str]]) -> Dict[str, int]:
    """Analyze the types of SQL queries executed."""
    query_types = {}

    for query in sql_log:
        sql = query.get("sql", "").upper().strip()

        # Determine query type
        if sql.startswith("SELECT COUNT"):
            query_type = "count"
        elif sql.startswith("SELECT DISTINCT") or "DISTINCT" in sql:
            query_type = "distinct"
        elif "GROUP BY" in sql:
            query_type = "group_by"
        elif "ORDER BY" in sql:
            query_type = "ordered"
        elif "WHERE" in sql:
            query_type = "filtered"
        elif sql.startswith("SELECT"):
            query_type = "basic_select"
        elif sql.startswith("WITH"):
            query_type = "cte"
        else:
            query_type = "other"

        query_types[query_type] = query_types.get(query_type, 0) + 1

    return query_types


def _create_error_report(
    error_msg: str, dataset_df: pd.DataFrame
) -> Dict[str, Any]:
    """Create an error report when analysis fails."""
    return {
        "headline": "EDA analysis failed due to technical error",
        "key_findings": [
            f"Analysis failed: {error_msg}",
            f"Dataset has {len(dataset_df)} rows and {len(dataset_df.columns)} columns",
        ],
        "risks": [
            "Analysis could not be completed",
            "Manual inspection required",
        ],
        "fixes": [],
        "data_quality_score": 0.0,
        "markdown": f"# EDA Analysis Failed\n\n**Error:** {error_msg}\n\nPlease check the dataset and configuration.",
        "column_profiles": {},
        "correlation_insights": [],
        "missing_data_analysis": {},
    }
