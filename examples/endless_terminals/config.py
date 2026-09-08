"""Validated configuration for bounded terminal-agent evaluations."""

from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class EvaluationConfig(BaseModel):
    """Select the task snapshot, inference backend, and evaluation limits."""

    mode: Literal["fixture", "endpoint", "kubernetes", "native"] = "fixture"
    data_directory: str = "data"
    output_directory: str = "runs"
    task_ids: list[str] = Field(default_factory=list)
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"
    model_revision: str = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
    base_url: Optional[str] = None
    cloud_config_path: Optional[str] = None
    baseline_artifact_id: Optional[UUID] = None
    max_actions: int = Field(default=16, ge=1, le=16)
    max_tokens: int = Field(default=2048, ge=1, le=2048)
    temperature: float = Field(default=0.6, ge=0, le=2)
    command_timeout: float = Field(default=10, gt=0, le=90)
    episode_timeout: float = Field(default=180, gt=0, le=1200)

    @model_validator(mode="after")
    def validate_backend(self) -> "EvaluationConfig":
        """Require the backend-specific configuration before any work starts.

        Returns:
            The validated configuration.

        Raises:
            ValueError: Required backend configuration is absent.
        """
        if (
            self.model_name != "Qwen/Qwen2.5-1.5B-Instruct"
            and "model_revision" not in self.model_fields_set
        ):
            raise ValueError(
                "A custom model requires its explicit model_revision"
            )
        if self.mode == "endpoint" and not self.base_url:
            raise ValueError("Endpoint mode requires base_url")
        if self.mode == "native" and type(self) is EvaluationConfig:
            raise ValueError("Native mode requires a training configuration")
        if self.mode == "kubernetes" and not self.cloud_config_path:
            raise ValueError("Kubernetes mode requires cloud_config_path")
        if len(self.model_revision) != 40 or any(
            character not in "0123456789abcdef"
            for character in self.model_revision
        ):
            raise ValueError("Use a pinned 40-character model revision")
        if len(self.task_ids) != len(set(self.task_ids)):
            raise ValueError("Task IDs must be unique")
        return self

    def resolve_directories(self) -> "EvaluationConfig":
        """Resolve paths before ZenML changes execution context.

        Returns:
            A copy with absolute data, output, and cloud configuration paths.
        """
        values = {
            "data_directory": str(Path(self.data_directory).resolve()),
            "output_directory": str(Path(self.output_directory).resolve()),
        }
        if self.cloud_config_path:
            values["cloud_config_path"] = str(
                Path(self.cloud_config_path).resolve()
            )
        return self.model_copy(update=values)


class TrainingConfig(EvaluationConfig):
    """Bound a small training-set demonstration with paired evaluations."""

    mode: Literal["kubernetes", "native"] = "kubernetes"
    prompt_variant: Literal["upstream", "concise_xml_v1"] = "upstream"
    training_task_ids: list[str] = Field(
        default_factory=lambda: [
            "task_000000_0228cd64",
            "task_000000_010b99da",
        ]
    )
    evaluation_attempts: int = Field(default=1, ge=1, le=20)
    groups: int = Field(default=16, ge=1, le=32)
    group_size: int = Field(default=4, ge=2, le=8)
    training_max_actions: int = Field(default=4, ge=1, le=16)
    zero_signal_patience: int = Field(default=4, ge=1, le=8)
    learning_rate: float = Field(default=1e-4, gt=0, le=1e-3)
    lora_rank: int = Field(default=8, ge=1, le=16)
    max_tokens: int = Field(default=1024, ge=1, le=2048)
    max_context: int = Field(default=8192, ge=4096, le=16384)
    temperature: float = Field(default=0.8, gt=0, le=2)
