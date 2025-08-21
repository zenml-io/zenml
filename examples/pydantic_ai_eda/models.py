"""Data models for EDA pipeline with Pydantic AI.

This module defines Pydantic models used throughout the EDA pipeline
for request/response handling, analysis results, and evaluation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DataSourceConfig(BaseModel):
    """Configuration for data source ingestion.

    Supports HuggingFace datasets, local files, and warehouse connections.

    Attributes:
        source_type: Type of data source (hf, local, warehouse)
        source_path: Path/identifier for the data source
        target_column: Optional target column for analysis focus
        sampling_strategy: How to sample the data (random, stratified, first_n)
        sample_size: Number of rows to sample (None for all data)
        warehouse_config: Additional config for warehouse connections
    """

    source_type: str = Field(
        description="Data source type: hf, local, or warehouse"
    )
    source_path: str = Field(
        description="Path or identifier for the data source"
    )
    target_column: Optional[str] = Field(
        None, description="Optional target column name"
    )
    sampling_strategy: str = Field("random", description="Sampling strategy")
    sample_size: Optional[int] = Field(
        None, description="Number of rows to sample"
    )
    warehouse_config: Optional[Dict[str, Any]] = Field(
        None, description="Warehouse connection config"
    )


class DataQualityFix(BaseModel):
    """Model for data quality issues and suggested fixes.

    Represents a specific data quality problem identified during analysis
    along with recommended remediation actions.

    Attributes:
        title: Short description of the issue
        rationale: Explanation of why this is a problem
        severity: Impact level (low, medium, high, critical)
        code_snippet: Optional code to address the issue
        affected_columns: Columns affected by this issue
        estimated_impact: Estimated impact on data quality (0-1)
    """

    title: str = Field(
        description="Short description of the data quality issue"
    )
    rationale: str = Field(description="Explanation of why this is a problem")
    severity: str = Field(
        description="Severity level: low, medium, high, critical"
    )
    code_snippet: Optional[str] = Field(
        None, description="Code to fix the issue"
    )
    affected_columns: List[str] = Field(
        description="Columns affected by this issue"
    )
    estimated_impact: float = Field(
        description="Estimated impact on data quality (0-1)"
    )


class EDAReport(BaseModel):
    """Model for comprehensive EDA report results.

    Contains the structured output from Pydantic AI analysis including
    findings, quality assessment, and recommendations.

    Attributes:
        headline: Executive summary of key findings
        key_findings: List of important discoveries about the data
        risks: Potential data quality or analysis risks identified
        fixes: Recommended fixes for data quality issues
        data_quality_score: Overall data quality score (0-100)
        markdown: Full markdown report for human consumption
        column_profiles: Statistical profiles for each column
        correlation_insights: Key correlation findings
        missing_data_analysis: Analysis of missing data patterns
    """

    headline: str = Field(description="Executive summary of key findings")
    key_findings: List[str] = Field(
        description="Important discoveries about the data"
    )
    risks: List[str] = Field(
        description="Potential risks identified in the data"
    )
    fixes: List[DataQualityFix] = Field(
        description="Recommended data quality fixes"
    )
    data_quality_score: float = Field(
        description="Overall quality score (0-100)"
    )
    markdown: str = Field(description="Full markdown report")
    column_profiles: Dict[str, Dict[str, Any]] = Field(
        description="Statistical profiles per column"
    )
    correlation_insights: List[str] = Field(
        description="Key correlation findings"
    )
    missing_data_analysis: Dict[str, Any] = Field(
        description="Missing data patterns"
    )


class QualityGateDecision(BaseModel):
    """Model for quality gate decision results.

    Represents the outcome of evaluating whether data quality meets
    requirements for downstream processing or model training.

    Attributes:
        passed: Whether the quality gate check passed
        quality_score: The computed data quality score
        decision_reason: Explanation for the pass/fail decision
        blocking_issues: Issues that caused failure (if failed)
        recommendations: Suggested next steps
        metadata: Additional decision metadata
    """

    passed: bool = Field(description="Whether quality gate passed")
    quality_score: float = Field(description="Computed data quality score")
    decision_reason: str = Field(description="Explanation for the decision")
    blocking_issues: List[str] = Field(
        description="Issues that caused failure"
    )
    recommendations: List[str] = Field(description="Recommended next steps")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class AgentConfig(BaseModel):
    """Configuration for Pydantic AI agent behavior.

    Controls how the EDA agent operates including model selection,
    tool usage limits, and safety constraints.

    Attributes:
        model_name: Name of the language model to use
        max_tool_calls: Maximum number of tool calls allowed
        sql_guard_enabled: Whether to enable SQL safety guards
        preview_limit: Maximum rows to show in data previews
        enable_plotting: Whether to enable chart/plot generation
        timeout_seconds: Maximum execution time in seconds
    """

    model_name: str = Field("gpt-5", description="Language model to use")
    max_tool_calls: int = Field(50, description="Maximum tool calls allowed")
    sql_guard_enabled: bool = Field(
        True, description="Enable SQL safety guards"
    )
    preview_limit: int = Field(10, description="Max rows in data previews")
    enable_plotting: bool = Field(
        False, description="Enable plotting capabilities"
    )
    timeout_seconds: int = Field(300, description="Max execution time")
