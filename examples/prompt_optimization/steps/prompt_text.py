"""Shared prompt text for the prompt optimization example.

This module centralizes the default system prompt and the user prompt
builder so both steps can reuse a single source of truth.
"""

from __future__ import annotations

import pandas as pd

# Canonical default system prompt used by the EDA agent when no custom prompt
# is provided. Kept identical to the original in run_eda_agent to preserve behavior.
DEFAULT_SYSTEM_PROMPT: str = """You are a data analyst. Perform quick but insightful EDA.

FOCUS ON:
- Data quality score (0-100) based on missing data and duplicates
- Key patterns and distributions
- Notable correlations or anomalies
- 2-3 actionable recommendations

Be concise but specific with numbers. Aim for quality insights, not exhaustive analysis."""


def build_user_prompt(main_ref: str, df: pd.DataFrame) -> str:
    """Build the user prompt for the EDA agent.

    Produces the same structured instructions used previously, including dataset
    shape metadata and the numbered action steps that guide the agent to use tools.

    Args:
        main_ref: Reference key for the stored dataset (e.g., 'Out[1]').
        df: The pandas DataFrame being analyzed, used to derive rows and columns.

    Returns:
        A formatted user prompt string guiding the agent through quick EDA steps.
    """
    rows, cols = df.shape
    return (
        f"Quick EDA analysis for dataset '{main_ref}' ({rows} rows, {cols} cols).\n\n"
        "STEPS (keep it fast):\n"
        f"1. display('{main_ref}') - check data structure  \n"
        f"2. describe('{main_ref}') - get key stats\n"
        f"3. run_sql('{main_ref}', 'SELECT COUNT(*) as total FROM dataset') - check row count\n"
        f"4. If multiple numeric columns: analyze_correlations('{main_ref}')\n\n"
        "Generate EDAReport with data quality score and 2-3 key insights."
    )
