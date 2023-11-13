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

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models import (
    ServiceAccountRequestModel,
    ServiceAccountResponseModel,
    ServiceAccountUpdateModel,
    UserRequestModel,
    UserResponseModel,
    UserUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.team_schemas import TeamAssignmentSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        APIKeySchema,
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
    api_keys: List["APIKeySchema"] = Relationship(
        back_populates="service_account",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_user_request(cls, model: UserRequestModel) -> "UserSchema":
        """Create a `UserSchema` from a `UserModel`.

        Args:
            model: The `UserModel` from which to create the schema.

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
        )

    @classmethod
    def from_service_account_request(
        cls, model: ServiceAccountRequestModel
    ) -> "UserSchema":
        """Create a `UserSchema` from a Service Account request.

        Args:
            model: The `ServiceAccountRequestModel` from which to create the
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
        )

    def update_user(self, user_update: UserUpdateModel) -> "UserSchema":
        """Update a `UserSchema` from a `UserUpdateModel`.

        Args:
            user_update: The `UserUpdateModel` from which to update the schema.

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

    def update_service_account(
        self, service_account_update: ServiceAccountUpdateModel
    ) -> "UserSchema":
        """Update a `UserSchema` from a `ServiceAccountUpdateModel`.

        Args:
            service_account_update: The `ServiceAccountUpdateModel` from which
                to update the schema.

        Returns:
            The updated `UserSchema`.
        """
        for field, value in service_account_update.dict(
            exclude_none=True
        ).items():
            setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(
        self, _block_recursion: bool = False, include_private: bool = False
    ) -> UserResponseModel:
        """Convert a `UserSchema` to a `UserResponseModel`.

        Args:
            _block_recursion: Don't recursively fill attributes
            include_private: Whether to include the user private information
                             this is to limit the amount of data one can get
                             about other users

        Returns:
            The converted `UserResponseModel`.
        """
        if _block_recursion:
            return UserResponseModel(
                id=self.id,
                external_user_id=self.external_user_id,
                name=self.name,
                active=self.active,
                is_service_account=self.is_service_account,
                email_opted_in=self.email_opted_in,
                email=self.email if include_private else None,
                hub_token=self.hub_token if include_private else None,
                full_name=self.full_name,
                created=self.created,
                updated=self.updated,
            )
        else:
            return UserResponseModel(
                id=self.id,
                external_user_id=self.external_user_id,
                name=self.name,
                active=self.active,
                is_service_account=self.is_service_account,
                email_opted_in=self.email_opted_in,
                email=self.email if include_private else None,
                hub_token=self.hub_token if include_private else None,
                teams=[t.to_model(_block_recursion=True) for t in self.teams],
                full_name=self.full_name,
                created=self.created,
                updated=self.updated,
                roles=[ra.role.to_model() for ra in self.assigned_roles],
            )

    def to_service_account_model(
        self, _block_recursion: bool = False
    ) -> ServiceAccountResponseModel:
        """Convert a `UserSchema` to a `ServiceAccountResponseModel`.

        Args:
            _block_recursion: Don't recursively fill attributes

        Returns:
            The converted `ServiceAccountResponseModel`.
        """
        if _block_recursion:
            return ServiceAccountResponseModel(
                id=self.id,
                name=self.name,
                description=self.description or "",
                active=self.active,
                created=self.created,
                updated=self.updated,
            )
        else:
            return ServiceAccountResponseModel(
                id=self.id,
                name=self.name,
                description=self.description or "",
                active=self.active,
                teams=[t.to_model(_block_recursion=True) for t in self.teams],
                created=self.created,
                updated=self.updated,
                roles=[ra.role.to_model() for ra in self.assigned_roles],
            )
