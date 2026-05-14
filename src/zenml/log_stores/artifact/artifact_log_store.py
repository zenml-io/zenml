#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Artifact log store implementation."""

import os
import re
from datetime import datetime
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    cast,
)
from uuid import UUID

from opentelemetry.sdk._logs.export import LogExporter

from zenml.artifact_stores import BaseArtifactStore, ObjectInfo
from zenml.enums import LoggingLevels, StackComponentType
from zenml.exceptions import DoesNotExistException
from zenml.log_stores import BaseLogStore
from zenml.log_stores.base_log_store import BaseLogStoreOrigin
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.log_stores.otel.otel_log_store import (
    OtelLogStore,
    OtelLogStoreOrigin,
)
from zenml.logger import get_logger
from zenml.models import LogsResponse
from zenml.utils.io_utils import sanitize_remote_path
from zenml.utils.logging_utils import LogEntry

ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

logger = get_logger(__name__)


LOGS_EXTENSION = ".log"
MERGED_LOG_FILE_NAME = f"merged{LOGS_EXTENSION}"
LEGACY_MERGED_LOG_SUFFIX = f"_merged{LOGS_EXTENSION}"
TEMPORARY_COMPOSE_LOG_PREFIX = ".zenml-compose-"
END_OF_STREAM_MESSAGE = "END_OF_STREAM"


def _get_log_object_name(object_info: "ObjectInfo") -> str:
    """Get the normalized name of a listed log object."""
    return object_info.relative_path.strip("/")


def is_temporary_log_object(object_info: "ObjectInfo") -> bool:
    """Whether a listed object is a temporary log compose object."""
    return _get_log_object_name(object_info).startswith(
        TEMPORARY_COMPOSE_LOG_PREFIX
    )


def is_deterministic_merged_log_object(
    object_info: "ObjectInfo",
) -> bool:
    """Whether a listed object is the deterministic merged log file."""
    return _get_log_object_name(object_info) == MERGED_LOG_FILE_NAME


def is_merged_log_object(object_info: "ObjectInfo") -> bool:
    """Whether a listed object is a merged log file."""
    name = _get_log_object_name(object_info)
    return is_deterministic_merged_log_object(object_info) or name.endswith(
        LEGACY_MERGED_LOG_SUFFIX
    )


def is_log_fragment_object(object_info: "ObjectInfo") -> bool:
    """Whether a listed object is a log fragment."""
    name = _get_log_object_name(object_info)
    return (
        name.endswith(LOGS_EXTENSION)
        and not is_merged_log_object(object_info)
        and not is_temporary_log_object(object_info)
    )


def sort_log_objects(objects: List["ObjectInfo"]) -> List["ObjectInfo"]:
    """Sort log objects in the same order as the previous filename sort."""
    return sorted(objects, key=_get_log_object_name)


def list_log_objects(
    artifact_store: "BaseArtifactStore", logs_uri: str
) -> List["ObjectInfo"]:
    """List log objects with a legacy fallback for custom stores.

    The optional artifact-store methods are new extension points. If a custom
    store already had an unrelated ``list_objects`` helper with a different
    return shape, this function falls back to the older filesystem-like log
    listing behavior instead of breaking log fetch/finalization.
    """
    try:
        objects = list(artifact_store.list_objects(logs_uri))
    except Exception as e:
        logger.debug(
            "Could not list log objects for %s through list_objects(): %s",
            logs_uri,
            e,
        )
    else:
        if all(isinstance(object_info, ObjectInfo) for object_info in objects):
            return objects
        logger.debug(
            "Artifact store %s returned unexpected list_objects() values for "
            "%s. Falling back to listdir().",
            artifact_store.name,
            logs_uri,
        )

    return _list_log_objects_with_legacy_methods(artifact_store, logs_uri)


def _list_log_objects_with_legacy_methods(
    artifact_store: "BaseArtifactStore", logs_uri: str
) -> List["ObjectInfo"]:
    """List log objects through the pre-acceleration artifact-store API."""
    if not artifact_store.exists(logs_uri):
        return []

    if not artifact_store.isdir(logs_uri):
        return [
            ObjectInfo(
                uri=logs_uri,
                relative_path=os.path.basename(logs_uri),
                size=artifact_store.size(logs_uri),
            )
        ]

    objects: List[ObjectInfo] = []
    for file_name in artifact_store.listdir(logs_uri):
        uri = os.path.join(logs_uri, str(file_name))
        if not artifact_store.isdir(uri):
            objects.append(
                ObjectInfo(
                    uri=uri,
                    relative_path=str(file_name),
                    size=artifact_store.size(uri),
                )
            )
    return objects


def prepare_logs_uri(
    artifact_store: "BaseArtifactStore",
    log_id: UUID,
) -> str:
    """Generates and prepares a URI for the log file or folder for a step.

    Args:
        artifact_store: The artifact store on which the artifact will be stored.
        log_id: The ID of the logs entity

    Returns:
        The URI of the log storage (file or folder).
    """
    logs_base_uri = os.path.join(artifact_store.path, "logs")

    if artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
        logs_uri = os.path.join(logs_base_uri, str(log_id))
    else:
        logs_uri = os.path.join(logs_base_uri, f"{log_id}{LOGS_EXTENSION}")

    return sanitize_remote_path(logs_uri)


def remove_ansi_escape_codes(text: str) -> str:
    """Auxiliary function to remove ANSI escape codes from a given string.

    Args:
        text: the input string

    Returns:
        the version of the input string where the escape codes are removed.
    """
    return ansi_escape.sub("", text)


def fetch_log_records(
    artifact_store: "BaseArtifactStore",
    logs_uri: str,
    limit: int,
) -> List[LogEntry]:
    """Fetches log entries.

    Args:
        artifact_store: The artifact store.
        logs_uri: The URI of the artifact (file or directory).
        limit: Maximum number of log entries to return.

    Returns:
        List of log entries.
    """
    log_entries = []

    for line in _stream_logs_line_by_line(artifact_store, logs_uri):
        if log_entry := parse_log_entry(line):
            log_entries.append(log_entry)

        if len(log_entries) >= limit:
            break

    return log_entries


def _stream_file_line_by_line(
    artifact_store: "BaseArtifactStore",
    logs_uri: str,
) -> Generator[str, None, None]:
    """Stream a single log file line by line."""
    with artifact_store.open(logs_uri, "r") as file:
        for line in file:
            yield line.rstrip("\n\r")


def _select_log_objects(objects: List["ObjectInfo"]) -> List["ObjectInfo"]:
    """Select which listed log objects should be read."""
    merged_objects = sort_log_objects(
        [
            object_info
            for object_info in objects
            if is_merged_log_object(object_info)
        ]
    )
    deterministic_merged_objects = [
        object_info
        for object_info in merged_objects
        if is_deterministic_merged_log_object(object_info)
    ]
    if deterministic_merged_objects:
        return deterministic_merged_objects
    if merged_objects:
        return merged_objects

    return sort_log_objects(
        [
            object_info
            for object_info in objects
            if is_log_fragment_object(object_info)
        ]
    )


def _stream_logs_line_by_line(
    artifact_store: "BaseArtifactStore",
    logs_uri: str,
) -> Generator[str, None, None]:
    """Stream logs line by line without loading the entire file into memory.

    This generator yields log lines one by one, handling both single files
    and directories with multiple log files.

    Args:
        artifact_store: The artifact store.
        logs_uri: The URI of the log file or directory.

    Yields:
        Individual log lines as strings.
    """
    if logs_uri.endswith(LOGS_EXTENSION):
        try:
            yield from _stream_file_line_by_line(artifact_store, logs_uri)
        except (DoesNotExistException, FileNotFoundError, IsADirectoryError):
            pass
        else:
            return

    log_objects = list_log_objects(artifact_store, logs_uri)
    if not log_objects:
        return

    for object_info in _select_log_objects(log_objects):
        try:
            yield from _stream_file_line_by_line(
                artifact_store, object_info.uri
            )
        except (DoesNotExistException, FileNotFoundError):
            continue


def parse_log_entry(log_line: str) -> Optional[LogEntry]:
    """Parse a single log entry into a LogEntry object.

    Handles two formats:
    1. JSON format: {"timestamp": "...", "level": "...", "message": "...", "location": "..."}
       Uses Pydantic's model_validate_json for automatic parsing and validation.
    2. Plain text: Any other text (defaults to INFO level)

    Args:
        log_line: A single log line to parse

    Returns:
        LogEntry object. For JSON logs, all fields are validated and parsed automatically.
        For plain text logs, only message is populated with INFO level default.
        Returns None only for empty lines.
    """
    line = log_line.strip()
    if not line:
        return None

    if line.startswith("{") and line.endswith("}"):
        try:
            return LogEntry.model_validate_json(line)
        except Exception:
            pass

    old_format = re.search(
        r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+UTC\]", line
    )

    timestamp = None
    if old_format:
        timestamp = old_format.group(1) + "Z"
        line = line.replace(old_format.group(0), "").strip()

    return LogEntry(
        message=line,
        name=None,
        level=LoggingLevels.INFO,
        timestamp=timestamp,
    )


class ArtifactLogStoreConfig(OtelLogStoreConfig):
    """Configuration for the artifact log store."""


class ArtifactLogStoreOrigin(OtelLogStoreOrigin):
    """Artifact log store origin."""

    def __init__(
        self,
        name: str,
        log_store: "BaseLogStore",
        log_model: LogsResponse,
        metadata: Dict[str, Any],
    ) -> None:
        """Initialize a log store origin.

        Args:
            name: The name of the origin.
            log_store: The log store to emit logs to.
            log_model: The log model associated with the origin.
            metadata: Additional metadata to attach to all log entries that will
                be emitted by this origin.
        """
        super().__init__(name, log_store, log_model, metadata)

        if log_model.uri:
            self.metadata["zenml.log.uri"] = log_model.uri


class ArtifactLogStore(OtelLogStore):
    """Log store that saves logs to the artifact store.

    This implementation extends OtelLogStore and uses the ArtifactLogExporter
    to write logs to the artifact store. Inherits all OTEL infrastructure
    including shared BatchLogRecordProcessor and routing.
    """

    def __init__(
        self, artifact_store: "BaseArtifactStore", *args: Any, **kwargs: Any
    ) -> None:
        """Initialize the artifact log store.

        Args:
            artifact_store: The artifact store to use for logging.
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        super().__init__(*args, **kwargs)
        self._artifact_store = artifact_store

    @property
    def origin_class(self) -> Type[ArtifactLogStoreOrigin]:
        """Class of the origin.

        Returns:
            The class of the origin.
        """
        return ArtifactLogStoreOrigin

    @classmethod
    def from_artifact_store(
        cls, artifact_store: "BaseArtifactStore"
    ) -> "ArtifactLogStore":
        """Creates an artifact log store from an artifact store.

        Args:
            artifact_store: The artifact store to create the log store from.

        Returns:
            The created artifact log store.
        """
        return cls(
            artifact_store=artifact_store,
            id=artifact_store.id,
            name="default",
            config=ArtifactLogStoreConfig(endpoint=artifact_store.path),
            flavor="artifact",
            type=StackComponentType.LOG_STORE,
            user=artifact_store.user,
            created=artifact_store.created,
            updated=artifact_store.updated,
        )

    @property
    def config(self) -> ArtifactLogStoreConfig:
        """Returns the configuration of the artifact log store.

        Returns:
            The configuration.
        """
        return cast(ArtifactLogStoreConfig, self._config)

    def get_exporter(self) -> "LogExporter":
        """Get the artifact log exporter for this log store.

        Returns:
            The ArtifactLogExporter instance.
        """
        from zenml.log_stores.artifact.artifact_log_exporter import (
            ArtifactLogExporter,
        )

        return ArtifactLogExporter(artifact_store=self._artifact_store)

    def _release_origin(
        self,
        origin: BaseLogStoreOrigin,
    ) -> None:
        """Finalize the stream of log records associated with an origin.

        Args:
            origin: The origin to finalize.
        """
        assert isinstance(origin, ArtifactLogStoreOrigin)
        with self._lock:
            origin.logger.emit(
                body=END_OF_STREAM_MESSAGE,
            )

    def fetch(
        self,
        logs_model: "LogsResponse",
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List["LogEntry"]:
        """Fetch logs from the artifact store.

        Args:
            logs_model: The logs model containing uri and artifact_store_id.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.

        Returns:
            List of log entries from the artifact store.

        Raises:
            ValueError: If logs_model.uri is not provided.
        """
        if not logs_model.uri:
            raise ValueError(
                "logs_model.uri is required for ArtifactLogStore.fetch()"
            )

        if not logs_model.artifact_store_id:
            raise ValueError(
                "logs_model.artifact_store_id is required "
                "for ArtifactLogStore.fetch()"
            )

        if logs_model.artifact_store_id != self._artifact_store.id:
            raise ValueError(
                "logs_model.artifact_store_id does not match the artifact store "
                "id of the log store."
            )

        if start_time or end_time:
            logger.warning(
                "start_time and end_time are not supported for "
                "ArtifactLogStore.fetch(). Both parameters will be ignored."
            )

        log_entries = fetch_log_records(
            artifact_store=self._artifact_store,
            logs_uri=logs_model.uri,
            limit=limit,
        )

        return log_entries

    def cleanup(self) -> None:
        """Cleanup the artifact log store.

        This method is called to ensure that the artifact log store is cleaned up.
        """
        self._artifact_store.cleanup()
