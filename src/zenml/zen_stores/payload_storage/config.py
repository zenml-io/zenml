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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Configuration of execution payload storage."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenml.utils.enum_utils import StrEnum


class PayloadBackendType(StrEnum):
    """Backends that can hold payload blobs."""

    DATABASE = "database"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"


class PayloadStorageConfiguration(BaseModel):
    """Configuration of the storage of execution payloads.

    Attributes:
        offload_enabled: Whether new snapshots, step runs and runs move their
            payloads to the write backend. Reads resolve offloaded payloads
            whatever this is set to, so it can be switched off again. Defaults
            to on for SQLite databases and off for MySQL databases, where it
            should only be switched on once every process that opens the
            database runs a version that can read offloaded payloads.
        write_backend: The backend that receives new payloads.
        backends: The backends holding payload blobs and their configuration.
            Every backend that ever received payloads must stay configured,
            since blobs are read from the backend they were written to. The
            `database` backend is always available and takes no
            configuration. `s3`, `gcs` and `azure` take the configuration of
            the artifact store flavor of the same name, such as a `path` like
            `s3://bucket/prefix` and optional credentials; without
            credentials, the implicit credentials of the environment are used.
        cache_size: The maximum memory in bytes taken by the resolved
            payloads that each process keeps. 0 disables the cache.
        timeout: The number of seconds to wait for the payload backend before
            failing a request. Payload storage that hangs then fails requests
            quickly instead of holding them.
    """

    offload_enabled: Optional[bool] = None
    write_backend: PayloadBackendType = PayloadBackendType.DATABASE
    backends: Dict[PayloadBackendType, Dict[str, Any]] = Field(
        default_factory=dict
    )
    cache_size: int = Field(default=128 * 1024 * 1024, ge=0)
    timeout: float = Field(default=30, gt=0)

    # Like the store configuration that holds it, so that a configuration
    # written by a newer release still loads.
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def _validate_write_backend(self) -> "PayloadStorageConfiguration":
        """Validate that the write backend is configured.

        Returns:
            The validated configuration.

        Raises:
            ValueError: If the write backend has no configuration.
        """
        if (
            self.write_backend != PayloadBackendType.DATABASE
            and self.write_backend not in self.backends
        ):
            raise ValueError(
                f"Payloads are written to the `{self.write_backend}` backend, "
                "which has no configuration in `backends`."
            )
        return self
