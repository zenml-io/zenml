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

from collections import defaultdict
from typing import DefaultDict, Dict, List, Set

from pydantic import Field, validator

from zenml.enums import StackComponentType
from zenml.utils.filesync_model import FileSyncModel
from zenml.zen_stores.models import (
    FlavorWrapper,
    Project,
    Role,
    RoleAssignment,
    Team,
    User,
)
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper


class ZenStorePipelineModel(FileSyncModel):
    """Pydantic object used for serializing ZenStore pipelines and runs.

    Attributes:
        pipeline_runs: Maps pipeline names to runs of that pipeline.
    """

    pipeline_runs: DefaultDict[str, List[PipelineRunWrapper]] = Field(
        default=defaultdict(list)
    )

    @validator("pipeline_runs")
    def _construct_pipeline_runs_defaultdict(
        cls, pipeline_runs: Dict[str, List[PipelineRunWrapper]]
    ) -> DefaultDict[str, List[PipelineRunWrapper]]:
        """Ensures that `pipeline_runs` is a defaultdict so runs
        of a new pipeline can be added without issues."""
        return defaultdict(list, pipeline_runs)

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes from configs of previous ZenML versions
        extra = "ignore"


class ZenStoreModel(FileSyncModel):
    """Pydantic object used for serializing a ZenStore.

    Attributes:
        version: zenml version number
        stacks: Maps stack names to a configuration object containing the
            names and flavors of all stack components.
        stack_components: Contains names and flavors of all registered stack
            components.
        stack_component_flavors: Contains the flavor definitions of each
            stack component type
        users: All registered users.
        teams: All registered teams.
        projects: All registered projects.
        roles: All registered roles.
        role_assignments: All role assignments.
        team_assignments: Maps team names to names of users that are part of
            the team.
    """

    stacks: Dict[str, Dict[StackComponentType, str]] = Field(
        default_factory=dict
    )
    stack_components: DefaultDict[StackComponentType, Dict[str, str]] = Field(
        default=defaultdict(dict)
    )
    stack_component_flavors: List[FlavorWrapper] = Field(default_factory=list)
    users: List[User] = Field(default_factory=list)
    teams: List[Team] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    roles: List[Role] = Field(default_factory=list)
    role_assignments: List[RoleAssignment] = Field(default_factory=list)
    team_assignments: DefaultDict[str, Set[str]] = Field(
        default=defaultdict(set)
    )

    @validator("stack_components")
    def _construct_stack_components_defaultdict(
        cls, stack_components: Dict[StackComponentType, Dict[str, str]]
    ) -> DefaultDict[StackComponentType, Dict[str, str]]:
        """Ensures that `stack_components` is a defaultdict so stack
        components of a new component type can be added without issues."""
        return defaultdict(dict, stack_components)

    @validator("team_assignments")
    def _construct_team_assignments_defaultdict(
        cls, team_assignments: Dict[str, Set[str]]
    ) -> DefaultDict[str, Set[str]]:
        """Ensures that `team_assignments` is a defaultdict so users
        of a new teams can be added without issues."""
        return defaultdict(set, team_assignments)

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes from configs of previous ZenML versions
        extra = "ignore"
