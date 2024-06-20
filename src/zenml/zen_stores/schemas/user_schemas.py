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

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlmodel import Field, Relationship

from zenml.models import (
    ServiceAccountRequest,
    ServiceAccountResponse,
    ServiceAccountResponseBody,
    ServiceAccountResponseMetadata,
    ServiceAccountUpdate,
    UserRequest,
    UserResponse,
    UserResponseBody,
    UserResponseMetadata,
    UserUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        ActionSchema,
        APIKeySchema,
        ArtifactVersionSchema,
        CodeRepositorySchema,
        EventSourceSchema,
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
        ServiceSchema,
        StackComponentSchema,
        StackSchema,
        StepRunSchema,
        TriggerSchema,
    )


class UserSchema(NamedSchema, table=True):
    """SQL Model for users."""

    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("name", "is_service_account"),)

    is_service_account: bool = Field(default=False)
    full_name: str
    description: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    email: Optional[str] = Field(nullable=True)
    active: bool
    password: Optional[str] = Field(nullable=True)
    activation_token: Optional[str] = Field(nullable=True)
    hub_token: Optional[str] = Field(nullable=True)
    email_opted_in: Optional[bool] = Field(nullable=True)
    external_user_id: Optional[UUID] = Field(nullable=True)
    is_admin: bool = Field(default=False)
    user_metadata: Optional[str] = Field(nullable=True)

    stacks: List["StackSchema"] = Relationship(back_populates="user")
    components: List["StackComponentSchema"] = Relationship(
        back_populates="user",
    )
    flavors: List["FlavorSchema"] = Relationship(back_populates="user")
    actions: List["ActionSchema"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "delete",
            "primaryjoin": "UserSchema.id==ActionSchema.user_id",
        },
    )
    event_sources: List["EventSourceSchema"] = Relationship(
        back_populates="user"
    )
    pipelines: List["PipelineSchema"] = Relationship(back_populates="user")
    schedules: List["ScheduleSchema"] = Relationship(
        back_populates="user",
    )
    runs: List["PipelineRunSchema"] = Relationship(back_populates="user")
    step_runs: List["StepRunSchema"] = Relationship(back_populates="user")
    builds: List["PipelineBuildSchema"] = Relationship(back_populates="user")
    artifact_versions: List["ArtifactVersionSchema"] = Relationship(
        back_populates="user"
    )
    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="user"
    )
    secrets: List["SecretSchema"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    triggers: List["TriggerSchema"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "delete",
            "primaryjoin": "UserSchema.id==TriggerSchema.user_id",
        },
    )
    auth_actions: List["ActionSchema"] = Relationship(
        back_populates="service_account",
        sa_relationship_kwargs={
            "cascade": "delete",
            "primaryjoin": "UserSchema.id==ActionSchema.service_account_id",
        },
    )
    deployments: List["PipelineDeploymentSchema"] = Relationship(
        back_populates="user",
    )
    code_repositories: List["CodeRepositorySchema"] = Relationship(
        back_populates="user",
    )
    services: List["ServiceSchema"] = Relationship(back_populates="user")
    service_connectors: List["ServiceConnectorSchema"] = Relationship(
        back_populates="user",
    )
    models: List["ModelSchema"] = Relationship(
        back_populates="user",
    )
    model_versions: List["ModelVersionSchema"] = Relationship(
        back_populates="user",
    )
    model_versions_artifacts_links: List["ModelVersionArtifactSchema"] = (
        Relationship(back_populates="user")
    )
    model_versions_pipeline_runs_links: List[
        "ModelVersionPipelineRunSchema"
    ] = Relationship(back_populates="user")
    auth_devices: List["OAuthDeviceSchema"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    api_keys: List["APIKeySchema"] = Relationship(
        back_populates="service_account",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_user_request(cls, model: UserRequest) -> "UserSchema":
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
            is_service_account=False,
            is_admin=model.is_admin,
            user_metadata=json.dumps(model.user_metadata)
            if model.user_metadata
            else None,
        )

    @classmethod
    def from_service_account_request(
        cls, model: ServiceAccountRequest
    ) -> "UserSchema":
        """Create a `UserSchema` from a Service Account request.

        Args:
            model: The `ServiceAccountRequest` from which to create the
                schema.

        Returns:
            The created `UserSchema`.
        """
        return cls(
            name=model.name,
            description=model.description or "",
            active=model.active,
            is_service_account=True,
            email_opted_in=False,
            full_name="",
            is_admin=False,
        )

    def update_user(self, user_update: UserUpdate) -> "UserSchema":
        """Update a `UserSchema` from a `UserUpdate`.

        Args:
            user_update: The `UserUpdate` from which to update the schema.

        Returns:
            The updated `UserSchema`.
        """
        for field, value in user_update.model_dump(exclude_unset=True).items():
            if field == "old_password":
                continue

            if field == "password":
                setattr(self, field, user_update.create_hashed_password())
            elif field == "activation_token":
                setattr(
                    self, field, user_update.create_hashed_activation_token()
                )
            elif field == "user_metadata":
                if value is not None:
                    self.user_metadata = json.dumps(value)
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def update_service_account(
        self, service_account_update: ServiceAccountUpdate
    ) -> "UserSchema":
        """Update a `UserSchema` from a `ServiceAccountUpdate`.

        Args:
            service_account_update: The `ServiceAccountUpdate` from which
                to update the schema.

        Returns:
            The updated `UserSchema`.
        """
        for field, value in service_account_update.model_dump(
            exclude_none=True
        ).items():
            setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        include_private: bool = False,
        **kwargs: Any,
    ) -> UserResponse:
        """Convert a `UserSchema` to a `UserResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic
            include_private: Whether to include the user private information
                             this is to limit the amount of data one can get
                             about other users

        Returns:
            The converted `UserResponse`.
        """
        metadata = None
        if include_metadata:
            metadata = UserResponseMetadata(
                email=self.email if include_private else None,
                hub_token=self.hub_token if include_private else None,
                external_user_id=self.external_user_id,
                user_metadata=json.loads(self.user_metadata)
                if self.user_metadata
                else {},
            )

        return UserResponse(
            id=self.id,
            name=self.name,
            body=UserResponseBody(
                active=self.active,
                full_name=self.full_name,
                email_opted_in=self.email_opted_in,
                is_service_account=self.is_service_account,
                created=self.created,
                updated=self.updated,
                is_admin=self.is_admin,
            ),
            metadata=metadata,
        )

    def to_service_account_model(
        self, include_metadata: bool = False, include_resources: bool = False
    ) -> ServiceAccountResponse:
        """Convert a `UserSchema` to a `ServiceAccountResponse`.

        Args:
             include_metadata: Whether the metadata will be filled.
             include_resources: Whether the resources will be filled.

        Returns:
             The converted `ServiceAccountResponse`.
        """
        metadata = None
        if include_metadata:
            metadata = ServiceAccountResponseMetadata(
                description=self.description or "",
            )

        body = ServiceAccountResponseBody(
            created=self.created,
            updated=self.updated,
            active=self.active,
        )

        return ServiceAccountResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )
