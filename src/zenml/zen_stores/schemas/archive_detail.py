# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Typed archived execution detail consumed by SQL response conversion.

Conversion reads a few payload columns either from the unarchived SQL row or
from its archived record. The payload protocols name exactly those columns,
so the ORM schemas and the frozen archive record models are checked against
one contract, and a converter cannot start relying on an ORM-only attribute
that archived reads would lack. Relationships stay on the retained SQL row.
"""

from typing import Dict, List, Mapping, Optional, Protocol, Sequence, TypeVar
from uuid import UUID

from zenml.exceptions import ExecutionRetentionIntegrityError
from zenml.zen_stores.schemas.base_schemas import BaseSchema

PayloadT = TypeVar("PayloadT")


class RunPayload(Protocol):
    """Run detail columns that response conversion reads."""

    @property
    def pipeline_configuration(self) -> Optional[str]:
        """Legacy inline pipeline configuration.

        Returns:
            Serialized configuration, or None when a snapshot owns it.
        """
        ...

    @property
    def client_environment(self) -> Optional[str]:
        """Legacy inline client environment.

        Returns:
            Serialized environment, or None when a snapshot owns it.
        """
        ...

    @property
    def orchestrator_environment(self) -> Optional[str]:
        """Orchestrator environment recorded for the run.

        Returns:
            Serialized environment, if recorded.
        """
        ...

    @property
    def exception_info(self) -> Optional[str]:
        """Failure details recorded for the run.

        Returns:
            Serialized exception information, if the run failed.
        """
        ...


class StepPayload(Protocol):
    """Step detail columns that response conversion reads."""

    @property
    def exception_info(self) -> Optional[str]:
        """Failure details recorded for the step.

        Returns:
            Serialized exception information, if the step failed.
        """
        ...

    @property
    def step_configuration(self) -> Optional[str]:
        """Legacy inline step configuration.

        Returns:
            Serialized merged configuration, or None when a snapshot owns it.
        """
        ...


class SnapshotPayload(Protocol):
    """Snapshot detail columns that response conversion reads."""

    @property
    def pipeline_configuration(self) -> str:
        """Pipeline configuration of the snapshot.

        Returns:
            Serialized configuration.
        """
        ...

    @property
    def client_environment(self) -> str:
        """Client environment captured with the snapshot.

        Returns:
            Serialized environment.
        """
        ...

    @property
    def pipeline_spec(self) -> Optional[str]:
        """Pipeline specification of the snapshot.

        Returns:
            Serialized specification, if recorded.
        """
        ...

    @property
    def source_code(self) -> Optional[str]:
        """Pipeline source code captured with the snapshot.

        Returns:
            Source code, if recorded.
        """
        ...

    @property
    def description(self) -> Optional[str]:
        """Snapshot description.

        Returns:
            Description, if set.
        """
        ...


class ConfigurationPayload(Protocol):
    """Configuration fields consumed by SQL response models."""

    @property
    def id(self) -> UUID:
        """Configuration identity.

        Returns:
            The configuration ID.
        """
        ...

    @property
    def index(self) -> int:
        """Position within the owning snapshot.

        Returns:
            The configuration index.
        """
        ...

    @property
    def name(self) -> str:
        """Step invocation name.

        Returns:
            The configuration name.
        """
        ...

    @property
    def config(self) -> str:
        """Serialized step configuration.

        Returns:
            The configuration JSON.
        """
        ...

    @property
    def snapshot_id(self) -> Optional[UUID]:
        """Owning snapshot of a static configuration.

        Returns:
            The snapshot ID, or None for a dynamic configuration.
        """
        ...

    @property
    def step_run_id(self) -> Optional[UUID]:
        """Owning step of a dynamic configuration.

        Returns:
            The step ID, or None for a static configuration.
        """
        ...


class BundleDetail:
    """Index verified archived detail by record type and identity."""

    def __init__(self) -> None:
        """Start an empty request-local index."""
        self.runs: Dict[UUID, RunPayload] = {}
        self.steps: Dict[UUID, StepPayload] = {}
        self.snapshots: Dict[UUID, SnapshotPayload] = {}
        self._configurations: Dict[UUID, List[ConfigurationPayload]] = {}
        self._dynamic_configurations: Dict[UUID, ConfigurationPayload] = {}

    def add_configuration(self, configuration: ConfigurationPayload) -> None:
        """Index one configuration under its snapshot or step owner.

        Args:
            configuration: Verified configuration with exactly one owner.
        """
        if configuration.snapshot_id is not None:
            owned = self._configurations.setdefault(
                configuration.snapshot_id, []
            )
            owned.append(configuration)
            owned.sort(key=lambda record: record.index)
        elif configuration.step_run_id is not None:
            self._dynamic_configurations[configuration.step_run_id] = (
                configuration
            )

    def run(self, row: BaseSchema) -> RunPayload:
        """Return the archived detail of a retained run.

        Args:
            row: Retained run identity.

        Returns:
            The verified run payload.
        """
        return self._require(self.runs, row)

    def step(self, row: BaseSchema) -> StepPayload:
        """Return the archived detail of a retained step.

        Args:
            row: Retained step identity.

        Returns:
            The verified step payload.
        """
        return self._require(self.steps, row)

    def snapshot(self, row: BaseSchema) -> SnapshotPayload:
        """Return the archived detail of a retained snapshot.

        Args:
            row: Retained snapshot identity.

        Returns:
            The verified snapshot payload.
        """
        return self._require(self.snapshots, row)

    @staticmethod
    def _require(index: Mapping[UUID, PayloadT], row: BaseSchema) -> PayloadT:
        """Look up a retained row's payload, failing closed when absent.

        Args:
            index: Payloads of one record type.
            row: Retained SQL identity.

        Returns:
            The verified payload with the same identity.

        Raises:
            ExecutionRetentionIntegrityError: The row is absent from the bundle.
        """
        payload = index.get(row.id)
        if payload is None:
            raise ExecutionRetentionIntegrityError(
                f"Archived execution detail is missing for {row.id}."
            )
        return payload

    def step_configurations(
        self, snapshot_id: UUID, include: Optional[Sequence[str]] = None
    ) -> Sequence[ConfigurationPayload]:
        """Return ordered static definitions for one snapshot.

        Args:
            snapshot_id: Owning snapshot identity.
            include: Configuration names to include; an empty value selects all.

        Returns:
            Matching configurations, or an empty tuple for a dynamic snapshot.
        """
        configurations = self._configurations.get(snapshot_id, [])
        if not include:
            return configurations
        names = set(include)
        return tuple(
            record for record in configurations if record.name in names
        )

    def step_configuration(
        self, step_id: UUID
    ) -> Optional[ConfigurationPayload]:
        """Return the definition owned by a dynamic step.

        Args:
            step_id: Owning step identity.

        Returns:
            The dynamic configuration, or None for a static or legacy step.
        """
        return self._dynamic_configurations.get(step_id)
