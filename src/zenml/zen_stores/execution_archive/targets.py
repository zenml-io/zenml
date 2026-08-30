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
"""The storage target of the execution archive.

Where archive objects go is server infrastructure: an artifact store
flavor, its configuration and a path prefix in the server configuration.
The server records that identity once, as an immutable target row keyed by
the digest of the configuration, and every archive points at the target it
was written to. Changing the configuration creates another target; archives
written to the previous one keep resolving against it. The server
authenticates to the destination with its own identity, never through a
stack component or a service connector a pipeline user could edit.
"""

import json
import threading
from typing import TYPE_CHECKING, Any, Dict, Optional, cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from zenml.artifact_stores import BaseArtifactStore
from zenml.config.server_config import ServerConfiguration
from zenml.enums import StackComponentType
from zenml.exceptions import ArchiveUnavailableError
from zenml.models.v2.misc.execution_archive import validate_relative_path
from zenml.stack.flavor import Flavor, validate_flavor_source
from zenml.stack.flavor_registry import FlavorRegistry
from zenml.stack.utils import (
    get_flavor_by_name_and_type_from_zen_store,
    validate_stack_component_config,
)
from zenml.zen_stores.execution_archive.codec import (
    canonical_json,
    sha256_digest,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ExecutionArchiveStateError,
)
from zenml.zen_stores.execution_archive.models import ArchiveObjectKind
from zenml.zen_stores.execution_archive.storage import (
    ArtifactStoreExecutionArchiveObjectStore,
    BaseExecutionArchiveObjectStore,
)
from zenml.zen_stores.schemas import ExecutionArchiveStorageTargetSchema

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStore


class ExecutionArchiveTargets:
    """Resolves the configured target and opens the object store of any.

    Targets are immutable, so an opened object store is kept for the life
    of the process; the store keeps one instance.
    """

    def __init__(self, store: "SqlZenStore") -> None:
        """Initialize the targets.

        Args:
            store: The SQL store holding the target rows.
        """
        self._store = store
        self._object_stores: Dict[UUID, BaseExecutionArchiveObjectStore] = {}
        self._current: Optional[UUID] = None
        self._lock = threading.Lock()

    def current(self) -> UUID:
        """The target new archives are written to.

        Resolved from the server configuration and recorded on first use;
        the probe write proves that the server can use the destination
        before any archive points at it.

        Returns:
            The target ID.

        Raises:
            ExecutionArchiveStateError: If no archive storage is configured
                or the configuration is not a valid artifact store one.
        """
        with self._lock:
            if self._current is not None:
                return self._current
        config = ServerConfiguration.get_server_config()
        if not config.execution_archive_flavor:
            raise ExecutionArchiveStateError(
                "No execution archive storage is configured. Set "
                "ZENML_SERVER_EXECUTION_ARCHIVE_FLAVOR and "
                "ZENML_SERVER_EXECUTION_ARCHIVE_CONFIGURATION on every "
                "server."
            )
        flavor = get_flavor_by_name_and_type_from_zen_store(
            zen_store=self._store,
            flavor_name=config.execution_archive_flavor,
            component_type=StackComponentType.ARTIFACT_STORE,
        )
        configuration = validate_stack_component_config(
            configuration_dict=config.execution_archive_configuration,
            flavor=flavor.name,
            component_type=StackComponentType.ARTIFACT_STORE,
            zen_store=self._store,
            validate_custom_flavors=True,
        )
        if configuration is None:
            raise ExecutionArchiveStateError(
                f"Flavor '{flavor.name}' produced no artifact store "
                "configuration."
            )
        target = ExecutionArchiveStorageTargetSchema(
            flavor=flavor.name,
            flavor_source=flavor.source,
            # The full validated configuration is frozen so later flavor
            # defaults cannot change where an existing target points.
            configuration=json.dumps(
                configuration.model_dump(mode="json"), sort_keys=True
            ),
            path_prefix=validate_relative_path(
                config.execution_archive_path_prefix
            ),
        )
        target.digest = sha256_digest(
            canonical_json(
                [
                    target.flavor,
                    target.flavor_source,
                    target.configuration,
                    target.path_prefix,
                ]
            )
        )
        target_id = self._record(target)
        with self._lock:
            self._current = target_id
        return target_id

    def object_store(self, target_id: UUID) -> BaseExecutionArchiveObjectStore:
        """Open the object store of a target, once.

        Args:
            target_id: The storage target.

        Returns:
            The object store of the target.

        Raises:
            ArchiveUnavailableError: If the target does not exist.
        """
        with self._lock:
            cached = self._object_stores.get(target_id)
        if cached is not None:
            return cached
        with Session(self._store.engine) as session:
            target = session.get(
                ExecutionArchiveStorageTargetSchema, target_id
            )
            if target is None:
                raise ArchiveUnavailableError(
                    f"Execution archive storage target {target_id} does not "
                    "exist."
                )
            object_store = build_object_store(
                target, workspace_id=self._store.get_deployment_id()
            )
        with self._lock:
            return self._object_stores.setdefault(target_id, object_store)

    def _record(self, target: ExecutionArchiveStorageTargetSchema) -> UUID:
        """Find the target row of a configuration or create it.

        Args:
            target: The target as configured.

        Returns:
            The ID of the recorded target.
        """
        with Session(self._store.engine) as session:
            existing = session.exec(
                select(ExecutionArchiveStorageTargetSchema.id).where(
                    col(ExecutionArchiveStorageTargetSchema.digest)
                    == target.digest
                )
            ).first()
            if existing is not None:
                return existing
        workspace_id = self._store.get_deployment_id()
        verify_target_access(
            build_object_store(target, workspace_id=workspace_id),
            workspace_id,
        )
        with Session(self._store.engine) as session:
            session.add(target)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return session.exec(
                    select(ExecutionArchiveStorageTargetSchema.id).where(
                        col(ExecutionArchiveStorageTargetSchema.digest)
                        == target.digest
                    )
                ).one()
            return target.id


def build_object_store(
    target: ExecutionArchiveStorageTargetSchema, *, workspace_id: UUID
) -> BaseExecutionArchiveObjectStore:
    """Instantiate the artifact store of a target.

    Args:
        target: The storage target.
        workspace_id: The workspace whose archives the store serves.

    Returns:
        The object store of the target.

    Raises:
        TypeError: If the recorded flavor is not an artifact store flavor.
    """
    flavor = _resolve_flavor(target)
    configuration = flavor.config_class(
        **cast(Dict[str, Any], json.loads(target.configuration))
    )
    artifact_store = flavor.implementation_class(
        name="execution-archive",
        id=target.id,
        config=configuration,
        flavor=target.flavor,
        type=StackComponentType.ARTIFACT_STORE,
        user=None,
        created=target.created,
        updated=target.updated,
    )
    if not isinstance(artifact_store, BaseArtifactStore):
        raise TypeError(
            f"Flavor '{target.flavor}' does not implement an artifact store."
        )
    return ArtifactStoreExecutionArchiveObjectStore(
        artifact_store,
        target_id=target.id,
        path_prefix=target.path_prefix,
        workspace_id=workspace_id,
    )


def _resolve_flavor(target: ExecutionArchiveStorageTargetSchema) -> Flavor:
    """Find the artifact store flavor of a target.

    Flavors ZenML ships (built-in and integration flavors) are found by
    name, so moving or renaming their classes never makes an archive
    unreadable. Only a custom flavor is loaded from the import path
    recorded when the target was created.

    Args:
        target: The storage target.

    Returns:
        The flavor.
    """
    registry = FlavorRegistry()
    for flavor_class in [
        *registry.builtin_flavors,
        *registry.integration_flavors,
    ]:
        flavor = flavor_class()
        if (
            flavor.name == target.flavor
            and flavor.type == StackComponentType.ARTIFACT_STORE
        ):
            return flavor
    _, flavor = validate_flavor_source(
        source=target.flavor_source,
        component_type=StackComponentType.ARTIFACT_STORE,
    )
    return flavor


def verify_target_access(
    object_store: BaseExecutionArchiveObjectStore, workspace_id: UUID
) -> None:
    """Prove that the server can write and read back one archive object.

    The probe object stays in the store: it is content-addressed, tiny, and
    proves write access, which a read-only check could not.

    Args:
        object_store: The object store to probe.
        workspace_id: The workspace the probe is written for.
    """
    payload = b"zenml-execution-archive-storage-probe-v1"
    object_ = object_store.put_if_absent(
        ArchiveObjectKind.PROBE, workspace_id, payload
    )
    object_store.get_exact(ArchiveObjectKind.PROBE, workspace_id, object_)
