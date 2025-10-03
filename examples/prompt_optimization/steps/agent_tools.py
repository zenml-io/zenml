"""Simple Pydantic AI agent tools for EDA analysis."""

import time
from dataclasses import dataclass, field
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

import duckdb
import pandas as pd
from pydantic_ai import ModelRetry, RunContext


@dataclass
class AnalystAgentDeps:
    """Simple storage for analysis results with Out[n] references."""

    output: Dict[str, pd.DataFrame] = field(default_factory=dict)
    query_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: int = 0
    started_at: float = field(default_factory=time.monotonic)
    time_budget_s: Optional[float] = None
    lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    def store(self, value: pd.DataFrame) -> str:
        """Store the output and return reference like Out[1] for the LLM."""
        with self.lock:
            ref = f"Out[{len(self.output) + 1}]"
            self.output[ref] = value
        return ref

    def get(self, ref: str) -> pd.DataFrame:
        if ref not in self.output:
            raise ModelRetry(
                f"Error: {ref} is not a valid variable reference. Check the previous messages and try again."
            )
        return self.output[ref]


def run_sql(ctx: RunContext[AnalystAgentDeps], dataset: str, sql: str) -> str:
    """Run SQL query on a DataFrame using DuckDB.

    Note: Use 'dataset' as the table name in your SQL queries.

    Args:
        ctx: Pydantic AI agent RunContext
        dataset: reference to the DataFrame (e.g., 'Out[1]')
        sql: SQL query to execute
    """
    try:
        data = ctx.deps.get(dataset)
        result = duckdb.query_df(
            df=data, virtual_table_name="dataset", sql_query=sql
        )
        df = result.df()
        rows = len(df)
        ref = ctx.deps.store(df)

        # Log the query for tracking
        ctx.deps.query_history.append(
            {"sql": sql, "result_ref": ref, "rows_returned": rows}
        )

        return f"Query executed successfully. Result stored as `{ref}` ({rows} rows)."
    except Exception as e:
        raise ModelRetry(f"SQL query failed: {str(e)}")


def display(
    ctx: RunContext[AnalystAgentDeps], dataset: str, rows: int = 5
) -> str:
    """Display the first few rows of a dataset.

    Args:
        ctx: Pydantic AI agent RunContext
        dataset: reference to the DataFrame
        rows: number of rows to display (default: 5)
    """
    try:
        data = ctx.deps.get(dataset)
        return f"Dataset {dataset} preview:\n{data.head(rows).to_string()}"
    except Exception as e:
        return f"Display error: {str(e)}"


def describe(ctx: RunContext[AnalystAgentDeps], dataset: str) -> str:
    """Get statistical summary of a dataset.

    Args:
        ctx: Pydantic AI agent RunContext
        dataset: reference to the DataFrame
    """
    try:
        data = ctx.deps.get(dataset)

        # Basic info
        info = [
            f"Dataset {dataset} comprehensive summary:",
            f"Shape: {data.shape[0]:,} rows × {data.shape[1]} columns",
            f"Memory usage: {data.memory_usage(deep=True).sum() / 1024**2:.2f} MB",
            "",
        ]

        # Data types and missing info
        info.append("Column Information:")
        for col in data.columns:
            dtype = str(data[col].dtype)
            null_count = data[col].isnull().sum()
            null_pct = (null_count / len(data)) * 100
            unique_count = data[col].nunique()

            info.append(
                f"  {col}: {dtype} | {null_count} nulls ({null_pct:.1f}%) | {unique_count} unique"
            )

        info.append("\nStatistical Summary:")
        info.append(data.describe(include="all").to_string())

        return "\n".join(info)
    except Exception as e:
        return f"Describe error: {str(e)}"


def analyze_correlations(
    ctx: RunContext[AnalystAgentDeps], dataset: str
) -> str:
    """Analyze correlations between numeric variables.

    Args:
        ctx: Pydantic AI agent RunContext
        dataset: reference to the DataFrame
    """
    try:
        data = ctx.deps.get(dataset)
        numeric_data = data.select_dtypes(include=["number"])

        if len(numeric_data.columns) < 2:
            return "Need at least 2 numeric columns for correlation analysis."

        corr_matrix = numeric_data.corr()

        # Store correlation matrix
        corr_ref = ctx.deps.store(corr_matrix)

        # Find strong correlations
        strong_corrs = []
        for i, col1 in enumerate(numeric_data.columns):
            for j, col2 in enumerate(numeric_data.columns[i + 1 :], i + 1):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    strong_corrs.append(f"{col1} ↔ {col2}: {corr_val:.3f}")

        result = [
            f"Correlation analysis for {len(numeric_data.columns)} numeric columns:",
            f"Correlation matrix stored as {corr_ref}",
            "",
        ]

        if strong_corrs:
            result.append("Strong correlations (|r| > 0.7):")
            result.extend(f"  {corr}" for corr in strong_corrs)
        else:
            result.append("No strong correlations (|r| > 0.7) found.")

        return "\n".join(result)
    except Exception as e:
        return f"Correlation analysis error: {str(e)}"


def budget_wrapper(max_tool_calls: Optional[int]):
    """Return a decorator that enforces time/tool-call budgets for tools.

    It reads `time_budget_s`, `started_at`, and `tool_calls` from ctx.deps and
    raises ModelRetry when limits are exceeded.
    """

    def with_budget(tool: Callable) -> Callable:
        @wraps(tool)
        def _wrapped(ctx: RunContext[AnalystAgentDeps], *args, **kwargs):
            # Enforce budgets atomically to be safe under parallel tool execution
            with ctx.deps.lock:
                tb = getattr(ctx.deps, "time_budget_s", None)
                if (
                    tb is not None
                    and (time.monotonic() - ctx.deps.started_at) > tb
                ):
                    raise ModelRetry("Time budget exceeded.")

                if (
                    max_tool_calls is not None
                    and ctx.deps.tool_calls >= max_tool_calls
                ):
                    raise ModelRetry("Tool-call budget exceeded.")

                # Increment tool call count after passing checks
                ctx.deps.tool_calls += 1

            # Execute the actual tool logic outside the lock
            return tool(ctx, *args, **kwargs)

        return _wrapped

    return with_budget


# Enhanced tool registry
AGENT_TOOLS = [run_sql, display, describe, analyze_correlations]
