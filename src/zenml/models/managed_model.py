"""Portable contracts for managed model serving.

Packages reference registered artifacts. Storage and provider credentials are
resolved by the backend and are deliberately absent from these contracts.
"""

from datetime import datetime
from typing import Annotated, Literal, Optional, Union
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from zenml.utils.time_utils import utc_now


class ManagedModelContract(BaseModel):
    """Strict, versioned input to managed serving operations."""

    model_config = ConfigDict(extra="forbid")


class ModelArtifactReference(ManagedModelContract):
    """Registered artifact and a directory relative to its storage root."""

    artifact_version_id: UUID
    path: str = "."

    @field_validator("path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        """Reject paths that escape the authorized artifact.

        Args:
            value: Artifact-relative directory.

        Returns:
            The validated directory.

        Raises:
            ValueError: If the path is absolute or ambiguous.
        """
        if value == ".":
            return value
        if (
            not value
            or value.startswith("/")
            or any(part in ("", ".", "..") for part in value.split("/"))
            or any(
                char in value for char in ("\\", ":", "\x00", "?", "#", "%")
            )
        ):
            raise ValueError("Use a relative artifact path without traversal.")
        return value


class HubModelReference(ManagedModelContract):
    """Public Hugging Face model pinned to an immutable commit."""

    repository: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")


class FullModelPackage(ManagedModelContract):
    """Transformers inference export with a separately identified tokenizer."""

    kind: Literal["transformers"] = "transformers"
    schema_version: Literal[1] = 1
    model: ModelArtifactReference
    tokenizer: ModelArtifactReference


class AdapterModelPackage(ManagedModelContract):
    """PEFT LoRA export with an exact base model and tokenizer."""

    kind: Literal["peft_lora"] = "peft_lora"
    schema_version: Literal[1] = 1
    model: ModelArtifactReference
    base_model: Union[ModelArtifactReference, HubModelReference]
    tokenizer: Union[ModelArtifactReference, HubModelReference]


ModelPackage = Annotated[
    Union[FullModelPackage, AdapterModelPackage], Field(discriminator="kind")
]


class ManagedModelRevisionRequest(ManagedModelContract):
    """Immutable package and approved runtime profile for a revision."""

    package: ModelPackage
    serving_profile: str = Field(min_length=1, max_length=128)


class ManagedModelServiceRequest(ManagedModelRevisionRequest):
    """Create intent scoped to a project and model-deployer component."""

    project_id: UUID
    model_deployer_id: UUID
    name: str = Field(min_length=1, max_length=255)


class ManagedModelMutation(ManagedModelContract):
    """Serialized lifecycle intent against an observed service generation."""

    action: Literal["update", "rollback", "pause", "resume", "delete", "retry"]
    expected_generation: int = Field(ge=1)
    revision: Optional[ManagedModelRevisionRequest] = None
    revision_id: Optional[UUID] = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "ManagedModelMutation":
        """Require exactly the payload appropriate to the operation.

        Returns:
            The validated mutation.

        Raises:
            ValueError: If the operation and payload disagree.
        """
        if (self.action == "update") != (self.revision is not None):
            raise ValueError("Only updates require a new revision.")
        if (self.action == "rollback") != (self.revision_id is not None):
            raise ValueError("Only rollbacks require a revision ID.")
        return self


class ManagedModelRevision(ManagedModelRevisionRequest):
    """Public immutable revision identity and creation timestamp."""

    id: UUID
    created: datetime


class ManagedModelOperation(BaseModel):
    """Public operation progress without provider internals or credentials."""

    id: UUID
    action: Literal[
        "create", "update", "rollback", "pause", "resume", "delete"
    ]
    status: Literal["pending", "running", "succeeded", "failed", "uncertain"]
    error: Optional[str] = None
    created: datetime = Field(default_factory=utc_now)


class ManagedModelService(BaseModel):
    """Stable model service with separately observed lifecycle progress."""

    id: UUID
    project_id: UUID
    model_deployer_id: UUID
    name: str
    generation: int
    desired_state: Literal["running", "paused", "deleted"]
    state: Literal[
        "pending", "ready", "paused", "failed", "deleting", "deleted"
    ]
    active_revision_id: Optional[UUID] = None
    serving_generation: Optional[int] = None
    prediction_url: Optional[str] = None
    operation: ManagedModelOperation
    revisions: list[ManagedModelRevision]
    created: datetime
    updated: datetime


class ManagedModelServicePage(BaseModel):
    """A bounded, project-scoped page of managed services."""

    items: list[ManagedModelService]
    total: int
    offset: int
    limit: int


class ManagedModelAdmission(BaseModel):
    """Authorized inference target without storage or provider information."""

    service_id: UUID
    generation: int
    revision_id: UUID
