#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Payload an archive moves out of SQL.

An execution payload holds the execution-specific columns of one family:
its runs, step runs and dynamic step configurations. A snapshot payload
holds the family's snapshots and their static step configurations. Both
keep the SQL identity of every row, so restoring and hydrating never match
rows by content.
"""

from typing import List, Literal, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ArchivedPipelineRunPayload(BaseModel):
    """Payload columns of one pipeline run."""

    id: UUID
    orchestrator_environment: Optional[str] = None
    exception_info: Optional[str] = None
    pipeline_configuration: Optional[str] = None
    client_environment: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class ArchivedStepRunPayload(BaseModel):
    """Payload columns of one step run."""

    id: UUID
    source_code: Optional[str] = None
    docstring: Optional[str] = None
    exception_info: Optional[str] = None
    step_configuration: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class ArchivedPipelineSnapshotPayload(BaseModel):
    """Payload columns of one pipeline snapshot."""

    id: UUID
    pipeline_configuration: str
    client_environment: str
    pipeline_spec: Optional[str] = None
    source_code: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class ArchivedStepConfigurationPayload(BaseModel):
    """One step configuration row, owned by a snapshot or a step run."""

    id: UUID
    snapshot_id: Optional[UUID] = None
    step_run_id: Optional[UUID] = None
    index: int
    name: str
    config: str

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _validate_single_owner(self) -> "ArchivedStepConfigurationPayload":
        """Require exactly one owner.

        Returns:
            The validated payload.

        Raises:
            ValueError: If the owner is missing or ambiguous.
        """
        if (self.snapshot_id is None) == (self.step_run_id is None):
            raise ValueError(
                "An archived step configuration needs exactly one owner."
            )
        return self


# Value compaction writes into a payload column instead of NULL, so the
# columns keep their NOT NULL constraint (changing it would rebuild the
# largest tables) and an archived value is never mistaken for a legitimately
# empty one. Rows carrying it are only served hydrated.
ARCHIVED_PAYLOAD_PLACEHOLDER = "zenml:execution-archive:archived"

# Column names moved by the archive, per schema. The `id` of each record is
# its identity and never cleared.
ARCHIVED_RUN_FIELDS: Tuple[str, ...] = (
    "orchestrator_environment",
    "exception_info",
    "pipeline_configuration",
    "client_environment",
)
ARCHIVED_STEP_FIELDS: Tuple[str, ...] = (
    "source_code",
    "docstring",
    "exception_info",
    "step_configuration",
)
ARCHIVED_SNAPSHOT_FIELDS: Tuple[str, ...] = (
    "pipeline_configuration",
    "client_environment",
    "pipeline_spec",
    "source_code",
)
ARCHIVED_CONFIGURATION_FIELDS: Tuple[str, ...] = ("config",)


def _require_unique(name: str, identifiers: List[UUID]) -> None:
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"Archive payload {name} IDs must be unique.")


class ExecutionPayload(BaseModel):
    """Execution-specific payload of one root execution family."""

    schema_version: Literal[1] = 1
    root_run_id: UUID
    runs: List[ArchivedPipelineRunPayload] = Field(min_length=1)
    steps: List[ArchivedStepRunPayload] = Field(default_factory=list)
    step_configurations: List[ArchivedStepConfigurationPayload] = Field(
        default_factory=list
    )

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _validate_references(self) -> "ExecutionPayload":
        """Reject duplicate records, a missing root and foreign configs.

        Returns:
            The validated payload.

        Raises:
            ValueError: If the root run is absent or a configuration is
                not owned by one of the steps.
        """
        _require_unique("pipeline_run", [record.id for record in self.runs])
        _require_unique("step_run", [record.id for record in self.steps])
        _require_unique(
            "step_configuration",
            [record.id for record in self.step_configurations],
        )
        if self.root_run_id not in {run.id for run in self.runs}:
            raise ValueError("The archive payload must contain its root run.")
        step_ids = {step.id for step in self.steps}
        if any(
            record.step_run_id not in step_ids
            for record in self.step_configurations
        ):
            raise ValueError(
                "An execution payload only holds the dynamic configurations "
                "of its own step runs."
            )
        return self


class SnapshotPayload(BaseModel):
    """The snapshots of one family with their static step configurations."""

    schema_version: Literal[1] = 1
    snapshots: List[ArchivedPipelineSnapshotPayload] = Field(
        default_factory=list
    )
    step_configurations: List[ArchivedStepConfigurationPayload] = Field(
        default_factory=list
    )

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _validate_references(self) -> "SnapshotPayload":
        """Reject duplicate records and foreign configurations.

        Returns:
            The validated payload.

        Raises:
            ValueError: If a configuration is not owned by one of the
                snapshots.
        """
        _require_unique(
            "pipeline_snapshot", [record.id for record in self.snapshots]
        )
        _require_unique(
            "step_configuration",
            [record.id for record in self.step_configurations],
        )
        snapshot_ids = {snapshot.id for snapshot in self.snapshots}
        if any(
            record.snapshot_id not in snapshot_ids
            for record in self.step_configurations
        ):
            raise ValueError(
                "A snapshot payload only holds the static configurations of "
                "its own snapshots."
            )
        return self
