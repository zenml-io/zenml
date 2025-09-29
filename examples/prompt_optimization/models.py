"""Simple data models for prompt optimization example."""

import os
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator


class DataSourceConfig(BaseModel):
    """Data source configuration."""

    source_type: str = Field(description="Data source type: hf or local")
    source_path: str = Field(
        description="Path or identifier for the data source"
    )
    target_column: Optional[str] = Field(
        None, description="Optional target column name"
    )
    sample_size: Optional[int] = Field(
        None, description="Number of rows to sample"
    )


def normalize_model_name(name: str) -> str:
    """Normalize a model name by stripping any leading provider prefix.

    This prevents accidental double-prefixing when constructing a provider:model id.

    Examples:
        - 'openai:gpt-4o-mini' -> 'gpt-4o-mini'
        - 'anthropic:claude-3-haiku-20240307' -> 'claude-3-haiku-20240307'
        - 'gpt-4o-mini' -> 'gpt-4o-mini' (unchanged)
    """
    if not isinstance(name, str):
        return name
    value = name.strip()
    if ":" in value:
        maybe_provider, remainder = value.split(":", 1)
        if maybe_provider.lower() in ("openai", "anthropic"):
            return remainder.strip()
    return value


def infer_provider(
    model_name: Optional[str] = None,
) -> Literal["openai", "anthropic"]:
    """Infer the provider from model-name hints first, then environment variables.

    Rules:
    - If `model_name` clearly references Claude → Anthropic.
    - If `model_name` clearly references GPT / -o models → OpenAI.
    - Otherwise use environment keys as tie-breakers.
    - If both or neither keys exist and there is no hint, default to OpenAI.
    """
    if isinstance(model_name, str):
        mn = model_name.lower().strip()
        # Handle common hints robustly
        if mn.startswith("claude") or "claude" in mn:
            return "anthropic"
        if mn.startswith("gpt") or "gpt-" in mn or "-o" in mn:
            # e.g., gpt-4o, gpt-4o-mini, gpt-4.1
            return "openai"

    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    if has_openai and not has_anthropic:
        return "openai"
    if has_anthropic and not has_openai:
        return "anthropic"

    # Both present or neither present → default to OpenAI for GPT-style defaults
    return "openai"


class AgentConfig(BaseModel):
    """AI agent configuration."""

    provider: Optional[Literal["openai", "anthropic"]] = Field(
        default=None,
        description="Optional model provider. If omitted, inferred from the model name or environment.",
    )
    model_name: str = Field("gpt-4o-mini", description="Language model to use")
    max_tool_calls: int = Field(6, description="Maximum tool calls allowed")
    timeout_seconds: int = Field(
        60, description="Max execution time in seconds"
    )

    @field_validator("model_name", mode="before")
    @classmethod
    def _normalize_model_name(cls, v: object) -> object:
        """Normalize the model name early to remove accidental provider prefixes."""
        if isinstance(v, str):
            return normalize_model_name(v)
        return v

    @model_validator(mode="before")
    @classmethod
    def _set_provider_from_prefix(cls, data: object) -> object:
        """If a provider prefix is present in model_name, capture it into `provider`.

        This preserves the user's explicit intent (e.g., 'openai:gpt-4o-mini')
        even though `model_name` is normalized by the field validator.
        """
        if not isinstance(data, dict):
            return data
        provider = data.get("provider")
        raw_name = data.get("model_name")
        if (provider is None or provider == "") and isinstance(raw_name, str):
            value = raw_name.strip()
            if ":" in value:
                maybe_provider = value.split(":", 1)[0].strip().lower()
                if maybe_provider in ("openai", "anthropic"):
                    data["provider"] = maybe_provider
        return data

    def model_id(self) -> str:
        """Return a 'provider:model' string, inferring the provider when necessary.

        Precedence:
        1) Explicit provider captured from model_name prefix or set via `provider`
        2) Heuristic inference using model_name hints or environment variables
        """
        # Normalize again defensively to avoid double-prefixing if callers mutate model_name later
        name = normalize_model_name(self.model_name)
        provider: Literal["openai", "anthropic"] = (
            self.provider
            if self.provider is not None
            else infer_provider(name)
        )
        return f"{provider}:{name}"


class EDAReport(BaseModel):
    """Simple EDA analysis report from AI agent."""

    headline: str = Field(description="Executive summary of key findings")
    key_findings: List[str] = Field(
        default_factory=list, description="Important discoveries"
    )
    data_quality_score: float = Field(
        description="Overall quality score (0-100)"
    )
    markdown: str = Field(description="Full markdown report")


class ScoringConfig(BaseModel):
    """Scoring config with weights, penalties, and caps."""

    weight_quality: float = Field(
        0.7,
        ge=0.0,
        description="Weight for the quality component.",
    )
    weight_speed: float = Field(
        0.2,
        ge=0.0,
        description="Weight for the speed/latency component.",
    )
    weight_findings: float = Field(
        0.1,
        ge=0.0,
        description="Weight for the findings coverage component.",
    )
    speed_penalty_per_second: float = Field(
        2.0,
        ge=0.0,
        description="Linear penalty (points per second) applied when computing a speed score.",
    )
    findings_score_per_item: float = Field(
        0.5,
        ge=0.0,
        description="Base points credited per key finding before applying weights.",
    )
    findings_cap: int = Field(
        20,
        ge=0,
        description="Maximum number of findings to credit when scoring.",
    )

    @property
    def normalized_weights(self) -> Tuple[float, float, float]:
        """Return (quality, speed, findings) weights normalized to sum to 1."""
        total = self.weight_quality + self.weight_speed + self.weight_findings
        if total <= 0:
            return (1.0, 0.0, 0.0)
        return (
            self.weight_quality / total,
            self.weight_speed / total,
            self.weight_findings / total,
        )


class VariantScore(BaseModel):
    """Score summary for a single prompt variant."""

    prompt_id: str = Field(
        description="Stable identifier for the variant (e.g., 'variant_1')."
    )
    prompt: str = Field(description="The system prompt text evaluated.")
    score: float = Field(description="Aggregate score used for ranking.")
    quality_score: float = Field(
        description="Quality score produced by the agent/report (0-100)."
    )
    execution_time: float = Field(
        ge=0.0, description="Execution time in seconds for the evaluation."
    )
    findings_count: int = Field(
        ge=0, description="Number of key findings counted for this run."
    )
    success: bool = Field(
        description="Whether the evaluation completed successfully."
    )
    error: Optional[str] = Field(
        None, description="Optional error message if success is False."
    )
