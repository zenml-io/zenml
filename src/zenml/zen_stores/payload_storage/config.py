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

from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenml.utils.enum_utils import StrEnum


class PayloadBackendType(StrEnum):
    """Object stores that can hold payload blobs."""

    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"


# The schemes of the paths of each backend, as the Helm chart accepts them.
PATH_SCHEMES: Dict[PayloadBackendType, Tuple[str, ...]] = {
    PayloadBackendType.S3: ("s3://",),
    PayloadBackendType.GCS: ("gs://",),
    PayloadBackendType.AZURE: ("az://", "abfs://"),
}


class PayloadStorageConfiguration(BaseModel):
    """Configuration of the storage of execution payloads.

    Without an object store, payloads stay in the rows of their entities.

    Attributes:
        offload_enabled: Whether new snapshots, step runs and runs move their
            payloads to the backend. Reads resolve offloaded payloads whatever
            this is set to, so it can be switched off again. Only switch it on
            once every process that opens the database runs a version that
            can read offloaded payloads, with the same backend configured.
        backend: The object store holding payload blobs: `s3`, `gcs` or
            `azure`. Required when offloading is enabled. Neither the backend
            nor the `path` of its configuration can change once it holds
            payloads, since blobs are read from where they were written: a
            store refuses to start then.
        backend_config: The `path` where blobs are written, such as
            `s3://bucket/prefix`, and the options of the fsspec filesystem of
            the backend: s3fs (such as `key`, `secret`, `client_kwargs`),
            gcsfs (such as `project`, `token`) or adlfs (such as
            `account_name`, `connection_string`). Without credentials, the
            implicit credentials of the environment are used. Credentials can
            change.
        cache_size: The maximum memory in bytes taken by the resolved
            payloads that each process keeps. 0 disables the cache.
        timeout: The number of seconds after which a call to the payload
            backend is cancelled, retries included, and the request fails.
            Payload storage that hangs then fails requests quickly instead of
            holding them and their threads. The default stays below the
            server's request timeout (20 seconds), so that the storage error
            reaches the client. After three failed calls in a row, calls to
            the backend also fail at once for this long, until one call finds
            it recovered.
    """

    offload_enabled: bool = False
    backend: Optional[PayloadBackendType] = None
    backend_config: Dict[str, Any] = Field(default_factory=dict)
    cache_size: int = Field(default=128 * 1024 * 1024, ge=0)
    timeout: float = Field(default=10, gt=0)

    # Like the store configuration that holds it, so that a configuration
    # written by a newer release still loads.
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def _validate_backend(self) -> "PayloadStorageConfiguration":
        """Validate that offloading has a backend, and a backend its path.

        Returns:
            The validated configuration.

        Raises:
            ValueError: If offloading is enabled without a backend, or the
                backend has no path of its own.
        """
        if self.offload_enabled and self.backend is None:
            raise ValueError(
                "Offloading payloads needs a `backend`: `s3`, `gcs` or "
                "`azure`."
            )
        if self.backend is not None:
            schemes = PATH_SCHEMES[self.backend]
            path = self.backend_config.get("path")
            if not isinstance(path, str) or not path.startswith(schemes):
                raise ValueError(
                    f"The `{self.backend.value}` payload backend needs a "
                    "`path` in its `backend_config` that starts with "
                    f"`{'` or `'.join(schemes)}`, such as "
                    f"`{schemes[0]}bucket/prefix`."
                )
        return self
