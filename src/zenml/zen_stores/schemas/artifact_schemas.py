#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""SQLModel implementation of artifact tables."""


from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Relationship

from zenml.enums import ArtifactType
from zenml.models import ArtifactRequestModel, ArtifactResponseModel
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.step_run_schemas import (
        StepRunInputArtifactSchema,
        StepRunOutputArtifactSchema,
    )


class ArtifactSchema(NamedSchema, table=True):
    """SQL Model for artifacts of steps."""

    __tablename__ = "artifact"

    artifact_store_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="artifact_store_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="artifacts")

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship(back_populates="artifacts")

    type: ArtifactType
    uri: str
    materializer: str
    data_type: str

    input_to_step_runs: List["StepRunInputArtifactSchema"] = Relationship(
        back_populates="artifact",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    output_of_step_runs: List["StepRunOutputArtifactSchema"] = Relationship(
        back_populates="artifact",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_request(
        cls, artifact_request: ArtifactRequestModel
    ) -> "ArtifactSchema":
        """Convert an `ArtifactRequestModel` to an `ArtifactSchema`.

        Args:
            artifact_request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=artifact_request.name,
            artifact_store_id=artifact_request.artifact_store_id,
            project_id=artifact_request.project,
            user_id=artifact_request.user,
            type=artifact_request.type,
            uri=artifact_request.uri,
            materializer=artifact_request.materializer,
            data_type=artifact_request.data_type,
        )

    def to_model(
        self, producer_step_run_id: Optional[UUID]
    ) -> ArtifactResponseModel:
        """Convert an `ArtifactSchema` to an `ArtifactModel`.

        Args:
            producer_step_run_id: The ID of the step run that produced this
                artifact.

        Returns:
            The created `ArtifactModel`.
        """
        return ArtifactResponseModel(
            id=self.id,
            name=self.name,
            artifact_store_id=self.artifact_store_id,
            user=self.user.to_model() if self.user else None,
            project=self.project.to_model(),
            type=self.type,
            uri=self.uri,
            materializer=self.materializer,
            data_type=self.data_type,
            created=self.created,
            updated=self.updated,
            producer_step_run_id=producer_step_run_id,
        )
