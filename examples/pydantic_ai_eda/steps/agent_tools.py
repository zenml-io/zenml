"""Pydantic AI agent tools for SQL-based EDA analysis.

This module provides the tools and dependencies that the Pydantic AI agent
uses to perform exploratory data analysis through SQL queries.
"""

import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
from pydantic import BaseModel

# Import RunContext for tool signatures
try:
    from pydantic_ai import RunContext
except ImportError:
    # Define a fallback if not available
    class RunContext:
        def __init__(self, deps):
            self.deps = deps


logger = logging.getLogger(__name__)


class AnalystAgentDeps(BaseModel):
    """Dependencies for the EDA analyst agent.

    Manages the agent's state including datasets, query history,
    and analysis outputs. Acts as the context/memory for the agent.

    Attributes:
        datasets: Mapping of reference names to DataFrames
        query_history: Log of executed SQL queries
        output_counter: Counter for generating unique output references
    """

    datasets: Dict[str, pd.DataFrame] = {}
    query_history: List[Dict[str, Any]] = []
    output_counter: int = 0

    class Config:
        arbitrary_types_allowed = True

    def store_dataset(self, df: pd.DataFrame, ref_name: str = None) -> str:
        """Store a dataset and return its reference name.

        Args:
            df: DataFrame to store
            ref_name: Optional custom reference name

        Returns:
            Reference name for the stored dataset
        """
        if ref_name is None:
            self.output_counter += 1
            ref_name = f"Out[{self.output_counter}]"

        self.datasets[ref_name] = df.copy()
        logger.info(f"Stored dataset as {ref_name} with shape {df.shape}")
        return ref_name

    def get_dataset(self, ref_name: str) -> Optional[pd.DataFrame]:
        """Retrieve a dataset by reference name."""
        return self.datasets.get(ref_name)

    def list_datasets(self) -> List[str]:
        """List all available dataset references."""
        return list(self.datasets.keys())

    def log_query(
        self,
        sql: str,
        result_ref: str,
        rows_returned: int,
        execution_time_ms: float,
    ):
        """Log an executed SQL query."""
        self.query_history.append(
            {
                "sql": sql,
                "result_ref": result_ref,
                "rows_returned": rows_returned,
                "execution_time_ms": execution_time_ms,
                "timestamp": pd.Timestamp.now().isoformat(),
            }
        )


def run_duckdb_query(
    ctx: RunContext[AnalystAgentDeps], dataset_ref: str, sql: str
) -> str:
    """Execute SQL query against a dataset using DuckDB.

    This is the primary tool the agent uses for data analysis.
    Provides read-only access with safety guards against harmful SQL.

    Args:
        deps: Agent dependencies containing datasets
        dataset_ref: Reference to the dataset to query
        sql: SQL query to execute

    Returns:
        Message describing the query execution and result location
    """
    import time

    start_time = time.time()

    deps = ctx.deps
    try:
        # Get the dataset
        df = deps.get_dataset(dataset_ref)
        if df is None:
            return f"Error: Dataset '{dataset_ref}' not found. Available: {deps.list_datasets()}"

        # Validate SQL query for safety
        if not _is_safe_sql(sql):
            return "Error: SQL query contains prohibited operations. Only SELECT queries are allowed."

        # Auto-inject LIMIT if missing and query might return large results
        modified_sql = _maybe_add_limit(sql, df)

        # Execute query with DuckDB
        conn = duckdb.connect(":memory:")

        # Register the dataset
        conn.register("dataset", df)

        # Execute the query
        try:
            result = conn.execute(modified_sql).fetchdf()
            execution_time = (time.time() - start_time) * 1000

            # Store result
            result_ref = deps.store_dataset(result)

            # Log the query
            deps.log_query(
                modified_sql, result_ref, len(result), execution_time
            )

            # Return success message
            rows_msg = f"{len(result)} row(s)" if len(result) != 1 else "1 row"
            return f"Executed SQL successfully. Result stored as {result_ref} with {rows_msg}. Use display('{result_ref}') to view."

        except Exception as e:
            return f"SQL execution error: {str(e)}"
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error in run_duckdb_query: {e}")
        return f"Tool error: {str(e)}"


def display_data(
    ctx: RunContext[AnalystAgentDeps], dataset_ref: str, max_rows: int = 10
) -> str:
    """Display a preview of a dataset.

    Shows the first few rows of a dataset in a readable format.
    Used by the agent to peek at data content.

    Args:
        deps: Agent dependencies
        dataset_ref: Reference to dataset to display
        max_rows: Maximum number of rows to show

    Returns:
        String representation of the dataset preview
    """
    deps = ctx.deps
    try:
        df = deps.get_dataset(dataset_ref)
        if df is None:
            return f"Error: Dataset '{dataset_ref}' not found. Available: {deps.list_datasets()}"

        if len(df) == 0:
            return f"Dataset {dataset_ref} is empty (0 rows, {len(df.columns)} columns)."

        # Show basic info
        preview_rows = min(max_rows, len(df))
        info = f"Dataset {dataset_ref}: {len(df)} rows × {len(df.columns)} columns\n\n"

        # Show column info
        info += "Columns and types:\n"
        for col, dtype in df.dtypes.items():
            null_count = df[col].isnull().sum()
            null_pct = null_count / len(df) * 100 if len(df) > 0 else 0
            info += f"  {col}: {dtype} ({null_count} nulls, {null_pct:.1f}%)\n"

        info += f"\nFirst {preview_rows} rows:\n"
        info += df.head(preview_rows).to_string(max_cols=10, max_colwidth=50)

        if len(df) > preview_rows:
            info += f"\n... ({len(df) - preview_rows} more rows)"

        return info

    except Exception as e:
        return f"Display error: {str(e)}"


def profile_data(ctx: RunContext[AnalystAgentDeps], dataset_ref: str) -> str:
    """Generate statistical profile of a dataset.

    Provides comprehensive statistics about the dataset including
    distributions, correlations, and data quality metrics.

    Args:
        ctx: Agent context with dependencies
        dataset_ref: Reference to dataset to profile

    Returns:
        Detailed statistical profile as string
    """
    deps = ctx.deps
    try:
        df = deps.get_dataset(dataset_ref)
        if df is None:
            return f"Error: Dataset '{dataset_ref}' not found. Available: {deps.list_datasets()}"

        if len(df) == 0:
            return f"Cannot profile empty dataset {dataset_ref}."

        profile = f"Statistical Profile for {dataset_ref}\n"
        profile += "=" * 50 + "\n\n"

        # Basic info
        profile += f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns\n"
        profile += f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n\n"

        # Numeric columns summary
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            profile += "Numeric Columns:\n"
            desc = df[numeric_cols].describe()
            profile += desc.to_string() + "\n\n"

        # Categorical columns summary
        cat_cols = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()
        if cat_cols:
            profile += "Categorical Columns:\n"
            for col in cat_cols[
                :5
            ]:  # Limit to first 5 to avoid too much output
                unique_count = df[col].nunique()
                null_count = df[col].isnull().sum()
                most_common = df[col].value_counts().head(3)

                profile += f"  {col}:\n"
                profile += f"    Unique values: {unique_count}\n"
                profile += f"    Null values: {null_count}\n"
                profile += f"    Most common: {dict(most_common)}\n\n"

        # Missing data analysis
        missing_data = df.isnull().sum()
        if missing_data.sum() > 0:
            profile += "Missing Data:\n"
            for col, missing in missing_data[missing_data > 0].items():
                pct = missing / len(df) * 100
                profile += f"  {col}: {missing} ({pct:.1f}%)\n"
            profile += "\n"

        # Correlation for numeric columns (if more than 1 numeric column)
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            # Find high correlations
            high_corrs = []
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols[i + 1 :], i + 1):
                    corr_val = corr_matrix.iloc[i, j]
                    if abs(corr_val) > 0.7:  # High correlation threshold
                        high_corrs.append((col1, col2, corr_val))

            if high_corrs:
                profile += "High Correlations (>0.7):\n"
                for col1, col2, corr in high_corrs:
                    profile += f"  {col1} ↔ {col2}: {corr:.3f}\n"
                profile += "\n"

        return profile

    except Exception as e:
        return f"Profile error: {str(e)}"


def save_table_as_csv(
    ctx: RunContext[AnalystAgentDeps], dataset_ref: str, filename: str = None
) -> str:
    """Save a dataset as CSV file.

    Optional tool for exporting analysis results. Saves to temporary
    directory and returns the file path.

    Args:
        ctx: Agent context with dependencies
        dataset_ref: Reference to dataset to save
        filename: Optional filename (auto-generated if not provided)

    Returns:
        Path to saved CSV file or error message
    """
    deps = ctx.deps
    try:
        df = deps.get_dataset(dataset_ref)
        if df is None:
            return f"Error: Dataset '{dataset_ref}' not found. Available: {deps.list_datasets()}"

        # Generate filename if not provided
        if filename is None:
            filename = f"eda_export_{dataset_ref.replace('[', '').replace(']', '')}.csv"

        # Ensure .csv extension
        if not filename.endswith(".csv"):
            filename += ".csv"

        # Save to temporary directory
        temp_dir = Path(tempfile.gettempdir()) / "zenml_eda_exports"
        temp_dir.mkdir(exist_ok=True)

        file_path = temp_dir / filename
        df.to_csv(file_path, index=False)

        return f"Saved {len(df)} rows to: {file_path}"

    except Exception as e:
        return f"Save error: {str(e)}"


def _is_safe_sql(sql: str) -> bool:
    """Check if SQL query is safe (read-only operations).

    Blocks potentially harmful SQL operations to ensure the agent
    can only perform analysis, not modify data or system state.
    """
    sql_upper = sql.upper().strip()

    # Allow only SELECT statements
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        return False

    # Block dangerous keywords
    prohibited_keywords = [
        "DROP",
        "DELETE",
        "INSERT",
        "UPDATE",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "REPLACE",
        "MERGE",
        "EXEC",
        "EXECUTE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "COPY",
        "IMPORT",
        "EXPORT",
        "LOAD",
        "INSTALL",
        "SET GLOBAL",
        "SET PERSIST",
    ]

    for keyword in prohibited_keywords:
        # Use word boundaries to avoid false positives
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, sql_upper):
            return False

    return True


def _maybe_add_limit(
    sql: str, df: pd.DataFrame, default_limit: int = 1000
) -> str:
    """Add LIMIT clause to queries that might return large results.

    Prevents the agent from accidentally creating huge result sets
    that could cause memory issues or slow performance.
    """
    sql_upper = sql.upper().strip()

    # If LIMIT already present, don't modify
    if "LIMIT" in sql_upper:
        return sql

    # If dataset is small, no need to limit
    if len(df) <= default_limit:
        return sql

    # Check if query might return large results
    # (GROUP BY, aggregation functions usually return smaller results)
    has_aggregation = any(
        keyword in sql_upper
        for keyword in [
            "GROUP BY",
            "COUNT(",
            "SUM(",
            "AVG(",
            "MAX(",
            "MIN(",
            "DISTINCT",
        ]
    )

    if has_aggregation:
        return sql

    # Add LIMIT clause
    modified_sql = sql.rstrip()
    if modified_sql.endswith(";"):
        modified_sql = modified_sql[:-1]

    return f"{modified_sql} LIMIT {default_limit}"


# Registry of available tools for the agent
AGENT_TOOLS = {
    "run_duckdb": run_duckdb_query,
    "display": display_data,
    "profile": profile_data,
    "save_csv": save_table_as_csv,
}
