"""Simple data models for prompt optimization example."""

from typing import List, Optional

from pydantic import BaseModel, Field


class DataSourceConfig(BaseModel):
    """Data source configuration."""

    source_type: str = Field(description="Data source type: hf or local")
    source_path: str = Field(description="Path or identifier for the data source")
    target_column: Optional[str] = Field(None, description="Optional target column name")
    sample_size: Optional[int] = Field(None, description="Number of rows to sample")


class AgentConfig(BaseModel):
    """AI agent configuration."""

    model_name: str = Field("gpt-4o-mini", description="Language model to use")
    max_tool_calls: int = Field(6, description="Maximum tool calls allowed")
    timeout_seconds: int = Field(60, description="Max execution time in seconds")


class EDAReport(BaseModel):
    """Simple EDA analysis report from AI agent."""

    headline: str = Field(description="Executive summary of key findings")
    key_findings: List[str] = Field(default_factory=list, description="Important discoveries")
    data_quality_score: float = Field(description="Overall quality score (0-100)")
    markdown: str = Field(description="Full markdown report")