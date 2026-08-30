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
"""One immutable archive target backed by an official artifact store."""

import posixpath
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from zenml.artifact_stores import BaseArtifactStore
from zenml.config.server_config import ServerConfiguration
from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES,
)
from zenml.enums import StackComponentType
from zenml.exceptions import ArchiveUnavailableError
from zenml.models import ExecutionArchiveObject
from zenml.models.v2.misc.execution_archive import validate_relative_path
from zenml.stack.flavor import Flavor
from zenml.stack.flavor_registry import FlavorRegistry
from zenml.utils import secret_utils
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.execution_archive.codec import (
    canonical_json,
    sha256_digest,
    verify_sha256,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ArchiveObjectInvalidError,
    ExecutionArchiveStateError,
)

_MAX_STORED_BYTES = (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES + 1024 * 1024
)
_ATTEMPT_OBJECT_NAME = re.compile(r"[1-9][0-9]*\.json\.gz")


@dataclass(frozen=True)
class ExecutionArchiveTarget:
    """Resolved immutable archive destination."""

    digest: str
    path_prefix: str
    workspace_id: UUID
    artifact_store: BaseArtifactStore


class ExecutionArchiveStorage:
    """Read, write, and delete generation-scoped archive objects."""

    def __init__(self, target: ExecutionArchiveTarget) -> None:
        """Initialize storage.

        Args:
            target: Resolved destination and identity.
        """
        self._target = target

    @property
    def target_digest(self) -> str:
        """Return the immutable target identity.

        Returns:
            SHA-256 digest of the resolved target configuration.
        """
        return self._target.digest

    def object_key(
        self, *, project_id: UUID, archive_id: UUID, claim_token: int
    ) -> str:
        """Return the immutable key of one archive write attempt.

        Args:
            project_id: Logical project owning the execution tree.
            archive_id: Archive generation ID.
            claim_token: Fencing token of the write attempt.

        Returns:
            Full artifact-store path of the object.

        Raises:
            ValueError: If the fencing token is not positive.
        """
        if claim_token <= 0:
            raise ValueError(
                "Execution archive claim tokens must be positive."
            )
        return posixpath.join(
            self.generation_prefix(
                project_id=project_id, archive_id=archive_id
            ),
            f"{claim_token}.json.gz",
        )

    def generation_prefix(self, *, project_id: UUID, archive_id: UUID) -> str:
        """Return the directory isolated to one archive generation.

        Args:
            project_id: Project that owns the generation.
            archive_id: Archive generation ID.

        Returns:
            Full generation directory.
        """
        return posixpath.join(
            self._target.artifact_store.path.rstrip("/"),
            self._target.path_prefix,
            "workspaces",
            str(self._target.workspace_id),
            "projects",
            str(project_id),
            "execution-archives",
            str(archive_id),
        )

    def write_verified(
        self, key: str, payload: bytes, *, decoded_bytes: int
    ) -> ExecutionArchiveObject:
        """Write one claimed generation and verify its exact bytes.

        A generation has one claimed writer and a unique key. Retrying an
        interrupted export safely overwrites an uncommitted partial object.

        Args:
            key: Full artifact-store object path.
            payload: Compressed archive bytes.
            decoded_bytes: Size before compression.

        Returns:
            Verified object metadata.

        Raises:
            ArchiveUnavailableError: If the object cannot be written and
                verified exactly.
        """
        try:
            self._target.artifact_store.makedirs(posixpath.dirname(key))
            with self._target.artifact_store.open(key, "wb") as stream:
                stream.write(payload)
        except Exception as e:
            raise ArchiveUnavailableError(
                f"Could not write execution archive object '{key}': {e}"
            ) from e
        object_ = ExecutionArchiveObject(
            sha256=sha256_digest(payload),
            stored_bytes=len(payload),
            decoded_bytes=decoded_bytes,
        )
        self.read_verified(key, object_)
        return object_

    def read_verified(
        self, key: str, object_: ExecutionArchiveObject
    ) -> bytes:
        """Read an object and verify its recorded size and digest.

        Args:
            key: Full artifact-store object path.
            object_: Expected object metadata.

        Returns:
            Exact compressed bytes.

        Raises:
            ArchiveObjectInvalidError: If the object's bytes do not match its
                recorded size or digest.
            ArchiveUnavailableError: If the object cannot be trusted.
        """
        if object_.stored_bytes > _MAX_STORED_BYTES:
            raise ArchiveUnavailableError(
                f"Execution archive object '{key}' exceeds the compressed "
                "object limit."
            )
        try:
            with self._target.artifact_store.open(key, "rb") as stream:
                payload = cast(bytes, stream.read(object_.stored_bytes + 1))
        except Exception as e:
            raise ArchiveUnavailableError(
                f"Could not read execution archive object '{key}': {e}"
            ) from e
        if len(payload) != object_.stored_bytes:
            raise ArchiveObjectInvalidError(
                f"Execution archive object '{key}' has {len(payload)} bytes "
                f"instead of {object_.stored_bytes}."
            )
        verify_sha256(payload, object_.sha256)
        return payload

    def delete(self, key: str) -> None:
        """Delete an archive object idempotently.

        Args:
            key: Full artifact-store object path.

        Raises:
            ArchiveUnavailableError: If a present object cannot be deleted.
        """
        try:
            self._target.artifact_store.remove(key)
        except FileNotFoundError:
            return
        except Exception as e:
            if not self._target.artifact_store.exists(key):
                return
            raise ArchiveUnavailableError(
                f"Could not delete execution archive object '{key}': {e}"
            ) from e

    def delete_other_attempts(self, committed_key: str) -> None:
        """Delete superseded fenced attempts for one archive generation.

        Only numeric attempt objects in the committed object's directory are
        eligible. This leaves unrelated objects untouched and makes retries
        safe if a previous writer lost its lease after uploading.

        Args:
            committed_key: Verified object key that must remain available.

        Raises:
            ArchiveUnavailableError: If the directory cannot be listed or an
                obsolete attempt cannot be deleted.
        """
        directory = posixpath.dirname(committed_key)
        committed_name = posixpath.basename(committed_key)
        try:
            entries = self._target.artifact_store.listdir(directory)
        except FileNotFoundError:
            return
        except Exception as e:
            raise ArchiveUnavailableError(
                "Could not list execution archive write attempts under "
                f"'{directory}': {e}"
            ) from e

        for entry in entries:
            name = posixpath.basename(str(entry))
            if (
                name == committed_name
                or _ATTEMPT_OBJECT_NAME.fullmatch(name) is None
            ):
                continue
            self.delete(posixpath.join(directory, name))


def build_execution_archive_storage(
    config: ServerConfiguration, *, workspace_id: UUID
) -> ExecutionArchiveStorage:
    """Build the configured archive target without registering a component.

    Args:
        config: Server configuration containing the archive destination.
        workspace_id: Immutable deployment namespace.

    Returns:
        Storage bound to the configured target.

    Raises:
        ExecutionArchiveStateError: If the target is absent or unsupported.
    """
    flavor_name = config.execution_archive_flavor
    if not flavor_name:
        raise ExecutionArchiveStateError(
            "No execution archive target is configured."
        )
    flavor = _official_artifact_store_flavor(flavor_name)
    configuration = flavor.config_class(
        **config.execution_archive_configuration
    )
    _require_ambient_identity(configuration)
    path_prefix = validate_relative_path(config.execution_archive_path_prefix)
    serialized_configuration = configuration.model_dump(
        mode="json", exclude_unset=True
    )
    digest = sha256_digest(
        canonical_json(
            {
                "flavor": flavor.name,
                "configuration": serialized_configuration,
                "path_prefix": path_prefix,
                "workspace_id": str(workspace_id),
            }
        )
    )
    now = utc_now()
    artifact_store = flavor.implementation_class(
        name="execution-archive",
        id=uuid5(NAMESPACE_URL, f"zenml:execution-archive:{digest}"),
        config=configuration,
        flavor=flavor.name,
        type=StackComponentType.ARTIFACT_STORE,
        user=None,
        created=now,
        updated=now,
        connector_requirements=flavor.service_connector_requirements,
        connector=None,
    )
    if not isinstance(artifact_store, BaseArtifactStore):
        raise ExecutionArchiveStateError(
            f"Flavor '{flavor.name}' is not an artifact store."
        )
    return ExecutionArchiveStorage(
        ExecutionArchiveTarget(
            digest=digest,
            path_prefix=path_prefix,
            workspace_id=workspace_id,
            artifact_store=artifact_store,
        )
    )


@lru_cache(maxsize=None)
def _official_artifact_store_flavor(name: str) -> Flavor:
    registry = FlavorRegistry()
    for flavor_class in (
        *registry.builtin_flavors,
        *registry.integration_flavors,
    ):
        flavor = flavor_class()
        if (
            flavor.name == name
            and flavor.type == StackComponentType.ARTIFACT_STORE
        ):
            return flavor
    raise ExecutionArchiveStateError(
        f"Execution archive flavor '{name}' is not an installed official "
        "artifact store flavor."
    )


def _require_ambient_identity(configuration: Any) -> None:
    values: Dict[str, Any] = configuration.model_dump()
    credential_fields = {
        name
        for name, field in configuration.__class__.model_fields.items()
        if secret_utils.is_secret_field(field)
    }
    credential_fields.add("authentication_secret")
    configured = sorted(
        name for name in credential_fields if values.get(name) is not None
    )
    if configured or configuration.required_secrets:
        fields = f" ({', '.join(configured)})" if configured else ""
        raise ExecutionArchiveStateError(
            "Execution archive credentials must come from the server's "
            "ambient identity; remove credential values and secret "
            f"references{fields}."
        )
