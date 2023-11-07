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
"""SQLModel implementation of user tables."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from zenml.models import (
    UserRequest,
    UserResponse,
    UserResponseBody,
    UserResponseMetadata,
    UserUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.team_schemas import TeamAssignmentSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        ArtifactSchema,
        CodeRepositorySchema,
        FlavorSchema,
        ModelSchema,
        ModelVersionArtifactSchema,
        ModelVersionPipelineRunSchema,
        ModelVersionSchema,
        OAuthDeviceSchema,
        PipelineBuildSchema,
        PipelineDeploymentSchema,
        PipelineRunSchema,
        PipelineSchema,
        RunMetadataSchema,
        ScheduleSchema,
        SecretSchema,
        ServiceConnectorSchema,
        StackComponentSchema,
        StackSchema,
        StepRunSchema,
        TeamSchema,
        UserRoleAssignmentSchema,
    )


class UserSchema(NamedSchema, table=True):
    """SQL Model for users."""

    __tablename__ = "user"

    full_name: str
    email: Optional[str] = Field(nullable=True)
    active: bool
    password: Optional[str] = Field(nullable=True)
    activation_token: Optional[str] = Field(nullable=True)
    hub_token: Optional[str] = Field(nullable=True)
    email_opted_in: Optional[bool] = Field(nullable=True)
    external_user_id: Optional[UUID] = Field(nullable=True)

    teams: List["TeamSchema"] = Relationship(
        back_populates="users", link_model=TeamAssignmentSchema
    )
    assigned_roles: List["UserRoleAssignmentSchema"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "delete"}
    )
    stacks: List["StackSchema"] = Relationship(back_populates="user")
    components: List["StackComponentSchema"] = Relationship(
        back_populates="user",
    )
    flavors: List["FlavorSchema"] = Relationship(back_populates="user")
    pipelines: List["PipelineSchema"] = Relationship(back_populates="user")
    schedules: List["ScheduleSchema"] = Relationship(
        back_populates="user",
    )
    runs: List["PipelineRunSchema"] = Relationship(back_populates="user")
    step_runs: List["StepRunSchema"] = Relationship(back_populates="user")
    builds: List["PipelineBuildSchema"] = Relationship(back_populates="user")
    artifacts: List["ArtifactSchema"] = Relationship(back_populates="user")
    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="user"
    )
    secrets: List["SecretSchema"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    deployments: List["PipelineDeploymentSchema"] = Relationship(
        back_populates="user",
    )
    code_repositories: List["CodeRepositorySchema"] = Relationship(
        back_populates="user",
    )
    service_connectors: List["ServiceConnectorSchema"] = Relationship(
        back_populates="user",
    )
    models: List["ModelSchema"] = Relationship(
        back_populates="user",
    )
    model_versions: List["ModelVersionSchema"] = Relationship(
        back_populates="user",
    )
    model_versions_artifacts_links: List[
        "ModelVersionArtifactSchema"
    ] = Relationship(back_populates="user")
    model_versions_pipeline_runs_links: List[
        "ModelVersionPipelineRunSchema"
    ] = Relationship(back_populates="user")
    auth_devices: List["OAuthDeviceSchema"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_request(cls, model: UserRequest) -> "UserSchema":
        """Create a `UserSchema` from a `UserRequest`.

        Args:
            model: The `UserRequest` from which to create the schema.

        Returns:
            The created `UserSchema`.
        """
        return cls(
            name=model.name,
            full_name=model.full_name,
            active=model.active,
            password=model.create_hashed_password(),
            activation_token=model.create_hashed_activation_token(),
            external_user_id=model.external_user_id,
            email_opted_in=model.email_opted_in,
            email=model.email,
        )

    def update(self, user_update: UserUpdate) -> "UserSchema":
        """Update a `UserSchema` from a `UserUpdate`.

        Args:
            user_update: The `UserUpdate` from which to update the schema.

        Returns:
            The updated `UserSchema`.
        """
        for field, value in user_update.dict(exclude_unset=True).items():
            if field == "password":
                setattr(self, field, user_update.create_hashed_password())
            elif field == "activation_token":
                setattr(
                    self, field, user_update.create_hashed_activation_token()
                )
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(
        self, hydrate: bool = False, include_private: bool = False
    ) -> UserResponse:
        """Convert a `UserSchema` to a `UserResponse`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.
            include_private: Whether to include the user private information
                             this is to limit the amount of data one can get
                             about other users

        Returns:
            The converted `UserResponse`.
        """
        metadata = None
        if hydrate:
            metadata = UserResponseMetadata(
                full_name=self.full_name,
                email=self.email if include_private else None,
                email_opted_in=self.email_opted_in,
                active=self.active,
                hub_token=self.hub_token if include_private else None,
                external_user_id=self.external_user_id,
            )

        return UserResponse(
            id=self.id,
            name=self.name,
            body=UserResponseBody(
                created=self.created,
                updated=self.updated,
            ),
            metadata=metadata,
        )
