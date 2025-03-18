#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""RBAC model classes."""

from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
)

from zenml.utils.enum_utils import StrEnum


class Action(StrEnum):
    """RBAC actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    READ_SECRET_VALUE = "read_secret_value"
    PRUNE = "prune"

    # Service connectors
    CLIENT = "client"

    # Models
    PROMOTE = "promote"

    # Secrets
    BACKUP_RESTORE = "backup_restore"

    SHARE = "share"


class ResourceType(StrEnum):
    """Resource types of the server API."""

    ACTION = "action"
    ARTIFACT = "artifact"
    ARTIFACT_VERSION = "artifact_version"
    CODE_REPOSITORY = "code_repository"
    EVENT_SOURCE = "event_source"
    FLAVOR = "flavor"
    MODEL = "model"
    MODEL_VERSION = "model_version"
    PIPELINE = "pipeline"
    PIPELINE_RUN = "pipeline_run"
    PIPELINE_DEPLOYMENT = "pipeline_deployment"
    PIPELINE_BUILD = "pipeline_build"
    RUN_TEMPLATE = "run_template"
    SERVICE = "service"
    RUN_METADATA = "run_metadata"
    SECRET = "secret"
    SERVICE_ACCOUNT = "service_account"
    SERVICE_CONNECTOR = "service_connector"
    STACK = "stack"
    STACK_COMPONENT = "stack_component"
    TAG = "tag"
    TRIGGER = "trigger"
    TRIGGER_EXECUTION = "trigger_execution"
    PROJECT = "project"
    # Deactivated for now
    # USER = "user"

    def is_project_scoped(self) -> bool:
        """Check if a resource type is project scoped.

        Returns:
            Whether the resource type is project scoped.
        """
        return self not in [
            self.FLAVOR,
            self.SECRET,
            self.SERVICE_CONNECTOR,
            self.STACK,
            self.STACK_COMPONENT,
            self.TAG,
            self.SERVICE_ACCOUNT,
            self.PROJECT,
            # Deactivated for now
            # self.USER,
        ]


class Resource(BaseModel):
    """RBAC resource model."""

    type: str
    id: Optional[UUID] = None
    project_id: Optional[UUID] = None

    def __str__(self) -> str:
        """Convert to a string.

        Returns:
            Resource string representation.
        """
        project_id = self.project_id

        if project_id:
            representation = f"{project_id}:"
        else:
            representation = ""
        representation += self.type
        if self.id:
            representation += f"/{self.id}"

        return representation

    @classmethod
    def parse(cls, resource: str) -> "Resource":
        """Parse an RBAC resource string into a Resource object.

        Args:
            resource: The resource to convert.

        Returns:
            The converted resource.
        """
        project_id: Optional[str] = None
        if ":" in resource:
            (
                project_id,
                resource_type_and_id,
            ) = resource.split(":", maxsplit=1)
        else:
            project_id = None
            resource_type_and_id = resource

        resource_id: Optional[str] = None
        if "/" in resource_type_and_id:
            resource_type, resource_id = resource_type_and_id.split("/")
        else:
            resource_type = resource_type_and_id

        return Resource(
            type=resource_type, id=resource_id, project_id=project_id
        )

    @model_validator(mode="after")
    def validate_project_id(self) -> "Resource":
        """Validate that project_id is set in combination with project-scoped resource types.

        Raises:
            ValueError: If project_id is not set for a project-scoped
                resource or set for an unscoped resource.

        Returns:
            The validated resource.
        """
        resource_type = ResourceType(self.type)

        if resource_type.is_project_scoped() and not self.project_id:
            raise ValueError(
                "project_id must be set for project-scoped resource type "
                f"'{self.type}'"
            )

        if not resource_type.is_project_scoped() and self.project_id:
            raise ValueError(
                "project_id must not be set for global resource type "
                f"'{self.type}'"
            )

        return self

    model_config = ConfigDict(frozen=True)
