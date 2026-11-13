"""Durable managed serving intents and private recovery checkpoints."""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.managed_models.state import ManagedModelDependency
from zenml.models.managed_model import (
    ManagedModelInferenceSecret,
    ManagedModelService,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field


class ManagedModelServiceSchema(BaseSchema, table=True):
    """Stable service document updated with a generation compare-and-swap."""

    __tablename__ = "managed_model_service"
    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="project",
        source_column="project_id",
        target_column="id",
        ondelete="RESTRICT",
        nullable=False,
    )
    model_deployer_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="stack_component",
        source_column="model_deployer_id",
        target_column="id",
        ondelete="RESTRICT",
        nullable=False,
    )
    inference_credentials: str = Field(
        default="{}",
        sa_column=Column(
            Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False
        ),
    )
    inference_key_hash: Optional[str] = Field(default=None, max_length=64)
    generation: int = Field(default=1)
    document: str = Field(
        sa_column=Column(
            Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False
        )
    )
    # Provider IDs are internal and never included in the public document.
    resources: str = Field(
        default="{}",
        sa_column=Column(
            Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False
        ),
    )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: object,
    ) -> ManagedModelService:
        """Decode the public service without exposing resource checkpoints.

        Args:
            include_metadata: Unused metadata flag.
            include_resources: Unused resource flag.
            **kwargs: Unused schema conversion flags.

        Returns:
            Public service representation.
        """
        service = ManagedModelService.model_validate_json(self.document)
        # Credential references are independent of worker lifecycle documents.
        reference = json.loads(self.inference_credentials).get("active")
        service.inference_secret = (
            ManagedModelInferenceSecret.model_validate(reference)
            if reference
            else None
        )
        return service


class ManagedModelOperationSchema(BaseSchema, table=True):
    """Idempotency record, lease and recoverable external mutation outcome."""

    __tablename__ = "managed_model_operation"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "request_key", name="uq_managed_model_request"
        ),
    )
    project_id: UUID = Field(index=True)
    service_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="managed_model_service",
        source_column="service_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    request_key: str = Field(max_length=STR_FIELD_MAX_LENGTH)
    request_hash: str = Field(max_length=64)
    generation: int
    action: str = Field(max_length=32)
    status: str = Field(default="pending", max_length=32, index=True)
    target_revision_id: Optional[UUID] = None
    lease_id: Optional[UUID] = None
    lease_expires_at: Optional[datetime] = None
    available_at: Optional[datetime] = None
    # Checkpoints contain resource identifiers, never source credential values.
    checkpoint: str = Field(
        default="{}",
        sa_column=Column(
            Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False
        ),
    )


class ManagedModelDependencySchema(BaseSchema, table=True):
    """Retain artifact, store and connector identities until owned resources are cleaned."""

    __tablename__ = "managed_model_dependency"
    __table_args__ = (
        UniqueConstraint(
            "service_id",
            "revision_id",
            "artifact_version_id",
            name="uq_managed_model_dependency",
        ),
    )
    service_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="managed_model_service",
        source_column="service_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    revision_id: UUID
    artifact_version_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="artifact_version",
        source_column="artifact_version_id",
        target_column="id",
        ondelete="RESTRICT",
        nullable=False,
    )
    artifact_store_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="stack_component",
        source_column="artifact_store_id",
        target_column="id",
        ondelete="RESTRICT",
        nullable=False,
    )
    connector_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="service_connector",
        source_column="connector_id",
        target_column="id",
        ondelete="RESTRICT",
        nullable=False,
    )
    uri: str = Field(sa_column=Column(Text, nullable=False))

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: object,
    ) -> ManagedModelDependency:
        """Decode the retained binding without credentials.

        Args:
            include_metadata: Unused metadata flag.
            include_resources: Unused resource flag.
            **kwargs: Unused schema conversion flags.

        Returns:
            Immutable source binding.
        """
        return ManagedModelDependency(
            artifact_version_id=self.artifact_version_id,
            artifact_store_id=self.artifact_store_id,
            connector_id=self.connector_id,
            uri=self.uri,
        )


class ManagedModelWorkspaceSchema(BaseSchema, table=True):
    """Durable admission gate preventing create-versus-teardown races."""

    __tablename__ = "managed_model_workspace"
    admission_open: bool = True
    drain_requested: bool = False
    transition_id: Optional[UUID] = None
