# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Index verified archived execution detail without storage dependencies."""

from typing import Any, ClassVar, Optional, Protocol, Sequence, cast
from uuid import UUID

from zenml.exceptions import ExecutionRetentionIntegrityError
from zenml.zen_stores.schemas.base_schemas import BaseSchema


class Record(Protocol):
    """Describe the identity shared by all archived record models."""

    id: UUID
    table: ClassVar[str]


class ConfigurationRecord(Record, Protocol):
    """Describe the configuration fields consumed by SQL response models."""

    index: int
    name: str
    config: str
    snapshot_id: Optional[UUID]
    step_run_id: Optional[UUID]


class BundleDetail:
    """Index one or more verified bundles by table and record identity."""

    def __init__(self, records: Sequence[Any]) -> None:
        """Build the record and configuration indexes.

        Args:
            records: Records whose integrity and closure were verified.
        """
        self.records: dict[str, dict[UUID, Record]] = {}
        self._configurations: dict[UUID, list[ConfigurationRecord]] = {}
        self._dynamic_configurations: dict[UUID, ConfigurationRecord] = {}
        self.extend(records)

    def extend(self, records: Sequence[Any]) -> None:
        """Merge verified records and order snapshot configurations.

        Args:
            records: Additional bundle records with globally unique identities.
        """
        for candidate in records:
            record = cast(Record, candidate)
            self.records.setdefault(record.table, {})[record.id] = record
            if record.table == "step_configuration":
                configuration = cast(ConfigurationRecord, record)
                if configuration.snapshot_id is not None:
                    configurations = self._configurations.setdefault(
                        configuration.snapshot_id, []
                    )
                    configurations.append(configuration)
                elif configuration.step_run_id is not None:
                    self._dynamic_configurations[configuration.step_run_id] = (
                        configuration
                    )
        for configurations in self._configurations.values():
            configurations.sort(key=lambda record: record.index)

    def record_for(self, row: BaseSchema) -> Record:
        """Return the archived payload for a retained SQL row.

        Args:
            row: Retained identity and table name from SQL.

        Returns:
            The verified payload with the same table and identity.

        Raises:
            ExecutionRetentionIntegrityError: The row is absent from the bundle.
        """
        record = self.records.get(str(row.__tablename__), {}).get(row.id)
        if record is None:
            raise ExecutionRetentionIntegrityError(
                f"Archived execution detail is missing for {row.id}."
            )
        return record

    def step_configurations(
        self, snapshot_id: UUID, include: Optional[Sequence[str]] = None
    ) -> Sequence[ConfigurationRecord]:
        """Return ordered static definitions for one snapshot.

        Args:
            snapshot_id: Owning snapshot identity.
            include: Configuration names to include; an empty value selects all.

        Returns:
            Matching configurations, or an empty tuple for a dynamic snapshot.
        """
        configurations = self._configurations.get(snapshot_id, ())
        if not include:
            return configurations
        names = set(include)
        return tuple(
            record for record in configurations if record.name in names
        )

    def step_configuration(
        self, step_id: UUID
    ) -> Optional[ConfigurationRecord]:
        """Return the definition owned by a dynamic step.

        Args:
            step_id: Owning step identity.

        Returns:
            The dynamic configuration, or None for a static or legacy step.
        """
        return self._dynamic_configurations.get(step_id)
