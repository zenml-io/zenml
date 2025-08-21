"""Simple data models for Pydantic AI EDA pipeline."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DataSourceConfig(BaseModel):
    """Simple data source configuration."""

    source_type: str = Field(
        description="Data source type: hf, local, or warehouse"
    )
    source_path: str = Field(
        description="Path or identifier for the data source"
    )
    target_column: Optional[str] = Field(
        None, description="Optional target column name"
    )
    sample_size: Optional[int] = Field(
        None, description="Number of rows to sample"
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
        default_factory=list,
        description="Important discoveries about the data",
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Potential risks identified in the data",
    )
    fixes: List[DataQualityFix] = Field(
        default_factory=list, description="Recommended data quality fixes"
    )
    data_quality_score: float = Field(
        description="Overall quality score (0-100)"
    )
    markdown: str = Field(description="Full markdown report")
    column_profiles: Optional[Dict[str, Dict[str, Any]]] = Field(
        default_factory=dict, description="Statistical profiles per column"
    )
    correlation_insights: List[str] = Field(
        default_factory=list, description="Key correlation findings"
    )
    missing_data_analysis: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Missing data patterns"
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
    """Simple configuration for Pydantic AI agent."""

    model_name: str = Field("gpt-4o-mini", description="Language model to use")
    max_tool_calls: int = Field(6, description="Maximum tool calls allowed")
    timeout_seconds: int = Field(
        60, description="Max execution time in seconds"
    )
