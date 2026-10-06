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
"""Offloading execution payloads to blob storage and loading them back."""

import hashlib
import time
from functools import partial
from typing import (
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    Optional,
    TypeVar,
)
from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from zenml.exceptions import (
    NonRetryablePayloadStorageError,
    PayloadIntegrityError,
    PayloadStorageUnavailableError,
)
from zenml.logger import get_logger
from zenml.zen_stores.payload_storage.blob_backends import (
    BlobBackend,
    create_blob_backend,
)
from zenml.zen_stores.payload_storage.cache import PayloadCache
from zenml.zen_stores.payload_storage.circuit_breaker import CircuitBreaker
from zenml.zen_stores.payload_storage.config import (
    BlobBackendType,
    PayloadStorageConfiguration,
)
from zenml.zen_stores.payload_storage.payloads import (
    OffloadResult,
    PayloadValue,
)
from zenml.zen_stores.schemas.payload_blob_schemas import (
    LOCATION_FINGERPRINT_LENGTH,
    PayloadBlobSchema,
)

IDENTITY_CODEC = "identity"
MAX_CONCURRENT_BACKEND_CALLS = 32
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
# Finished chunks are kept, so a retry after a timeout continues where
# the last attempt stopped.
BLOB_CHUNK_SIZE = 4 * MAX_CONCURRENT_BACKEND_CALLS
BLOB_QUERY_BATCH_SIZE = 500

T = TypeVar("T")
R = TypeVar("R")

logger = get_logger(__name__)


def _batched(
    items: Collection[T], size: int = BLOB_QUERY_BATCH_SIZE
) -> Iterable[List[T]]:
    """Split items into batches.

    Args:
        items: The items to split.
        size: The largest batch.

    Yields:
        The batches.
    """
    batch = list(items)
    for start in range(0, len(batch), size):
        yield batch[start : start + size]


class PayloadStore:
    """Offloads execution payloads to blob storage and loads them back.

    Each distinct payload value is stored once, as a blob addressed by its
    SHA-256. The `payload_blob` table registers a blob only once its bytes
    are durable, so a reference never points to missing bytes.
    """

    def __init__(
        self, engine: Engine, config: PayloadStorageConfiguration
    ) -> None:
        """Initializes the payload store.

        Args:
            engine: The engine of the database holding the blob registry.
            config: The payload storage configuration.
        """
        self._engine = engine
        self._offload_enabled = config.offload_enabled
        self._cache = PayloadCache(max_bytes=config.cache_max_bytes)
        self._timeout = config.backend_timeout_seconds
        # All None while no backend is configured and payloads stay inline.
        self._backend: Optional[BlobBackend] = None
        self._breaker: Optional[CircuitBreaker] = None
        self._location_fingerprint: Optional[str] = None
        if config.backend:
            self._backend = create_blob_backend(
                config.backend,
                config.backend_config,
                max_concurrent_calls=MAX_CONCURRENT_BACKEND_CALLS,
            )
            self._location_fingerprint = self._compute_location_fingerprint(
                config.backend, self._backend.location
            )
            self._breaker = CircuitBreaker(
                config.backend.value,
                failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                recovery_timeout_seconds=config.backend_timeout_seconds,
            )

    @property
    def offload_enabled(self) -> bool:
        """Whether new payloads are offloaded to the backend.

        Returns:
            Whether new payloads are offloaded.
        """
        return self._offload_enabled

    @property
    def backend_configured(self) -> bool:
        """Whether a backend is configured, so that blobs can be read.

        Returns:
            Whether a backend is configured.
        """
        return self._backend is not None

    def validate_storage_location(self) -> None:
        """Check that every blob is stored at the configured location.

        Raises:
            RuntimeError: If blobs are stored elsewhere, or exist while no
                backend is configured.
        """
        if not inspect(self._engine).has_table(
            PayloadBlobSchema.__tablename__
        ):
            return

        query = select(PayloadBlobSchema.location_fingerprint)
        if self._location_fingerprint:
            query = query.where(
                PayloadBlobSchema.location_fingerprint
                != self._location_fingerprint
            )
        with Session(self._engine) as session:
            location_fingerprint = session.exec(query.limit(1)).first()
        if location_fingerprint:
            raise RuntimeError(
                self._describe_location_mismatch(location_fingerprint)
            )

    def offload(self, values: Iterable[PayloadValue]) -> OffloadResult:
        """Store payload values as blobs, before a transaction references them.

        New bytes are written to the backend first, then registered in a
        short transaction of their own. If the referencing transaction fails
        later, the next write of the same content reuses the blob. The caller
        must not hold a transaction, since this waits for the backend.

        Args:
            values: The values to offload.

        Returns:
            The blob of each value.
        """
        if not self._offload_enabled:
            return OffloadResult.inline_only()
        backend = self._backend
        assert backend

        values_by_sha256 = {value.sha256: value for value in values}
        blob_ids: Dict[str, UUID] = {}
        if values_by_sha256:
            with Session(self._engine) as session:
                blob_ids = self._get_registered_blob_ids(
                    values_by_sha256, session=session
                )
            new_values = [
                value
                for sha256, value in values_by_sha256.items()
                if sha256 not in blob_ids
            ]
            deadline = time.monotonic() + self._timeout
            for chunk in _batched(new_values, BLOB_CHUNK_SIZE):
                self._call_backend(
                    partial(
                        backend.put_many,
                        {value.sha256: value.utf8_bytes for value in chunk},
                        timeout=deadline - time.monotonic(),
                    )
                )
                with Session(self._engine) as session:
                    registered = self._register_blobs(chunk, session)
                blob_ids.update(registered)
                # Only values written here: a blob that is merely registered
                # may miss its object, which a read has to detect.
                for sha256, blob_id in registered.items():
                    self._cache.put(blob_id, values_by_sha256[sha256].text)

        return OffloadResult(
            blob_ids_by_text={
                values_by_sha256[sha256].text: blob_id
                for sha256, blob_id in blob_ids.items()
            }
        )

    def get_cached(self, blob_ids: Collection[UUID]) -> Dict[UUID, str]:
        """Get the values of blobs that this process has cached.

        Args:
            blob_ids: The blobs to get.

        Returns:
            The cached values by blob ID.
        """
        return self._cache.get_cached(blob_ids)

    def load(self, blob_ids: Collection[UUID]) -> Dict[UUID, str]:
        """Load the values of blobs, from the cache or from storage.

        The registry is read in a short session of its own and the backend
        outside of it, so the caller must not hold a transaction. One
        deadline, the backend timeout from now, covers the whole load,
        including waits for concurrent loads of the same blobs and loads
        again after they failed.

        Args:
            blob_ids: The blobs to load.

        Returns:
            The values by blob ID.
        """
        return self._cache.get_or_load(
            blob_ids,
            self._load_uncached_payloads,
            deadline=time.monotonic() + self._timeout,
        )

    def _get_registered_blob_ids(
        self, sha256s: Collection[str], session: Session
    ) -> Dict[str, UUID]:
        """Get the IDs of the blobs already registered for some contents.

        Args:
            sha256s: The SHA-256 of each content.
            session: The session to use.

        Returns:
            The blob IDs by SHA-256.
        """
        blob_ids: Dict[str, UUID] = {}
        for batch in _batched(sha256s):
            for blob_id, sha256 in session.exec(
                select(PayloadBlobSchema.id, PayloadBlobSchema.sha256).where(
                    col(PayloadBlobSchema.sha256).in_(batch)
                )
            ):
                blob_ids[sha256] = blob_id
        return blob_ids

    def _build_blob_record(self, value: PayloadValue) -> PayloadBlobSchema:
        """Build the registry row of a payload value, without saving it.

        Args:
            value: The payload value.

        Returns:
            The registry row.
        """
        assert self._location_fingerprint
        return PayloadBlobSchema(
            sha256=value.sha256,
            codec=IDENTITY_CODEC,
            size_bytes=len(value.utf8_bytes),
            location_fingerprint=self._location_fingerprint,
        )

    def _register_blobs(
        self, values: List[PayloadValue], session: Session
    ) -> Dict[str, UUID]:
        """Register the blobs of payload values whose bytes are durable.

        Args:
            values: The payload values.
            session: The session to register them with.

        Returns:
            The blob IDs by SHA-256.
        """
        # Sorted, so that concurrent writers lock the same keys in the same
        # order and never deadlock each other.
        values = sorted(values, key=lambda value: value.sha256)
        blobs = [self._build_blob_record(value) for value in values]
        # Read now: the commit expires the rows, and reading them later would
        # query each one again.
        blob_ids = {blob.sha256: blob.id for blob in blobs}
        session.add_all(blobs)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            # A concurrent writer registered some of the same content first.
            return {
                value.sha256: self._get_or_register_blob_id(value)
                for value in values
            }
        return blob_ids

    def _get_or_register_blob_id(self, value: PayloadValue) -> UUID:
        """Register the blob of a payload value unless it already exists.

        Args:
            value: The payload value.

        Returns:
            The ID of the blob.

        Raises:
            IntegrityError: If the insert failed for another reason than a
                concurrent registration.
        """
        with Session(self._engine) as session:
            blob = self._build_blob_record(value)
            # Read now: the commit expires the row.
            blob_id = blob.id
            session.add(blob)
            try:
                session.commit()
                return blob_id
            except IntegrityError:
                session.rollback()
                # The rollback ended the transaction, so this read sees the
                # blob registered by the concurrent writer.
                existing = session.exec(
                    select(PayloadBlobSchema.id).where(
                        PayloadBlobSchema.sha256 == value.sha256
                    )
                ).first()
                if existing is None:
                    raise
                return existing

    def _load_uncached_payloads(
        self, blob_ids: Collection[UUID], deadline: float
    ) -> Dict[UUID, str]:
        """Load blobs that are not cached from the backend.

        Args:
            blob_ids: The blobs to load.
            deadline: The `time.monotonic()` by which the blobs are loaded.

        Returns:
            The values by blob ID.

        Raises:
            RuntimeError: If a blob is not registered.
            NonRetryablePayloadStorageError: If a blob is stored at another
                location than the configured one.
        """
        blobs: List[PayloadBlobSchema] = []
        with Session(self._engine) as session:
            for batch in _batched(blob_ids):
                blobs.extend(
                    session.exec(
                        select(PayloadBlobSchema).where(
                            col(PayloadBlobSchema.id).in_(batch)
                        )
                    )
                )
        if missing := set(blob_ids) - {blob.id for blob in blobs}:
            raise RuntimeError(
                f"Payload blobs {sorted(str(blob_id) for blob_id in missing)} "
                "are referenced but not registered."
            )
        for blob in blobs:
            if blob.location_fingerprint != self._location_fingerprint:
                raise NonRetryablePayloadStorageError(
                    self._describe_location_mismatch(blob.location_fingerprint)
                )
        backend = self._backend
        assert backend

        blobs_by_sha256 = {blob.sha256: blob for blob in blobs}
        values: Dict[UUID, str] = {}
        for chunk in _batched(sorted(blobs_by_sha256), BLOB_CHUNK_SIZE):
            data = self._call_backend(
                partial(
                    backend.get_many,
                    chunk,
                    timeout=deadline - time.monotonic(),
                )
            )
            for sha256 in chunk:
                blob = blobs_by_sha256[sha256]
                values[blob.id] = self._verify_and_decode(blob, data[sha256])
                # Cached at once, so that a retry after a later chunk failed
                # does not load this one again.
                self._cache.put(blob.id, values[blob.id])
        return values

    @staticmethod
    def _verify_and_decode(blob: PayloadBlobSchema, data: bytes) -> str:
        """Verify the bytes of a blob against its registry row and decode them.

        Args:
            blob: The registry row of the blob.
            data: The bytes read for the blob.

        Returns:
            The payload value.

        Raises:
            PayloadIntegrityError: If the bytes are not the registered ones.
        """
        if blob.codec != IDENTITY_CODEC:
            raise PayloadIntegrityError(
                f"Payload blob `{blob.id}` is encoded with the unsupported "
                f"codec `{blob.codec}`."
            )
        if (
            len(data) != blob.size_bytes
            or hashlib.sha256(data).hexdigest() != blob.sha256
        ):
            raise PayloadIntegrityError(
                f"The bytes of payload blob `{blob.id}` at payload storage "
                f"location `{blob.location_fingerprint}` do not match its "
                "registered size and SHA-256."
            )
        return data.decode("utf-8")

    def _call_backend(self, function: Callable[[], R]) -> R:
        """Call the backend through the circuit breaker.

        Args:
            function: The backend call.

        Returns:
            The result of the call.

        Raises:
            PayloadStorageUnavailableError: If the call fails or does not
                return in time, or the circuit breaker paused the backend.
            NonRetryablePayloadStorageError: If the storage refuses the call
                for good, such as for a missing object or denied access.
        """
        assert self._breaker
        try:
            with self._breaker.guard():
                return function()
        except PayloadStorageUnavailableError:
            # The circuit breaker paused the backend and already logged why.
            raise
        except (FileNotFoundError, PermissionError) as e:
            logger.warning("Execution payload storage refused a call: %s", e)
            # A 500 rather than a 503: retrying brings back neither a missing
            # object nor access.
            raise NonRetryablePayloadStorageError(
                f"Execution payload storage refused the request: {e}"
            ) from e
        except Exception as e:
            logger.warning("Execution payload storage failed a call: %s", e)
            raise PayloadStorageUnavailableError(
                f"Execution payload storage failed: {e}"
            ) from e

    @staticmethod
    def _compute_location_fingerprint(
        backend_type: BlobBackendType, location: str
    ) -> str:
        """Compute the fingerprint that blob rows record for a location.

        The backend and a digest of the location, cut to the length of the
        column: at least 10 hex digits of the digest remain.

        Args:
            backend_type: The backend holding the blobs.
            location: The location of the blobs.

        Returns:
            The location fingerprint.
        """
        digest = hashlib.sha256(location.encode("utf-8")).hexdigest()
        return f"{backend_type.value}:{digest}"[:LOCATION_FINGERPRINT_LENGTH]

    def _describe_location_mismatch(self, location_fingerprint: str) -> str:
        """Describe blobs stored at another location than the configured one.

        Args:
            location_fingerprint: The fingerprint of the blobs' location.

        Returns:
            The error message.
        """
        if self._backend:
            configured = (
                f"not at the configured `{self._backend.location}` "
                f"(`{self._location_fingerprint}`)"
            )
        else:
            configured = "but no payload storage backend is configured"
        return (
            "Execution payloads are stored at the payload storage location "
            f"`{location_fingerprint}`, {configured}. Configure the `backend` "
            "and `path` that they were written to: payload storage cannot "
            "move once it holds payloads."
        )
