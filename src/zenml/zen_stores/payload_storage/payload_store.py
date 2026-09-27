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
"""Offloading of execution payloads to blobs and their resolution."""

import hashlib
from concurrent.futures import (
    FIRST_COMPLETED,
    Future,
    ThreadPoolExecutor,
    wait,
)
from typing import (
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
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
# Failed backend calls in a row after which calls to the backend are paused.
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
# How much longer than a call's own timeout a batch waits for any call to
# return: calls that time out are then always seen, and counted by the
# circuit breaker, before the batch gives up.
BACKEND_STALL_MARGIN_SECONDS = 1.0
# Bounds the size of the `IN` lists of registry queries.
BLOB_QUERY_BATCH_SIZE = 500

T = TypeVar("T")
R = TypeVar("R")

logger = get_logger(__name__)


def _batched(items: Collection[T]) -> Iterable[List[T]]:
    """Split items into batches for `IN` lists.

    Args:
        items: The items to split.

    Yields:
        The batches.
    """
    batch = list(items)
    for start in range(0, len(batch), BLOB_QUERY_BATCH_SIZE):
        yield batch[start : start + BLOB_QUERY_BATCH_SIZE]


class PayloadStore:
    """Offloads the payloads of execution schemas and loads them back.

    Payloads are stored as content-addressed blobs in an object store: each
    distinct value is stored once. The `blob` table registers every blob, and
    a blob is only registered once its bytes are durable, so that a reference
    never points to missing bytes.
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
        self._backend: Optional[BlobBackend] = None
        # The location of the blobs as `blob.location_fingerprint` records it; None
        # keeps payloads inline.
        self._location_fingerprint: Optional[str] = None
        self._breaker: Optional[CircuitBreaker] = None
        if config.backend:
            self._backend = create_blob_backend(
                config.backend,
                config.backend_config,
                timeout=config.backend_timeout_seconds,
                max_concurrent_calls=MAX_CONCURRENT_BACKEND_CALLS,
            )
            self._location_fingerprint = self._compute_location_fingerprint(
                config.backend, self._backend.location
            )
            # Paused for as long as a call may take.
            self._breaker = CircuitBreaker(
                config.backend.value,
                failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                recovery_timeout_seconds=config.backend_timeout_seconds,
            )
        self._cache = PayloadCache(max_bytes=config.cache_max_bytes)
        self._timeout = config.backend_timeout_seconds
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_BACKEND_CALLS,
            thread_name_prefix="zenml-payload-storage",
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
        """Verify that every blob is stored at the configured location.

        Raises:
            RuntimeError: If blobs are stored at another location, or no
                backend is configured while blobs exist.
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

    @staticmethod
    def _compute_location_fingerprint(
        backend_type: BlobBackendType, location: str
    ) -> str:
        """Identify a location of blobs as the `location_fingerprint` of their rows.

        The backend and a digest of the location, cut to the length of the
        column: however long the location is, at least 10 hex digits of the
        digest remain.

        Args:
            backend_type: The backend holding the blobs.
            location: The location of the blobs.

        Returns:
            The identity of the location.
        """
        digest = hashlib.sha256(location.encode("utf-8")).hexdigest()
        return f"{backend_type.value}:{digest}"[:LOCATION_FINGERPRINT_LENGTH]

    def _describe_location_mismatch(self, location_fingerprint: str) -> str:
        """Describe blobs stored at another location than the configured one.

        Args:
            location_fingerprint: The location of the blobs, as their rows record it.

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
            f"`{location_fingerprint}`, {configured}. Configure the `backend` and `path` "
            "that they were written to: payload storage cannot move once it "
            "holds payloads."
        )

    def offload(self, values: Iterable[PayloadValue]) -> OffloadResult:
        """Store payload values ahead of the transaction referencing them.

        The bytes of new values are stored in the backend first. Their blobs
        are then registered in a short transaction of their own. If the
        transaction referencing them fails afterwards, the unreferenced blobs
        are reused by the next write of the same content. No transaction may
        be open while this runs, since it waits for the backend.

        Args:
            values: The values to offload.

        Returns:
            The offloaded payloads, which reference the blobs from schemas.
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
            if new_values:
                self._call_backend_batch(
                    lambda value: backend.put(value.sha256, value.utf8_bytes),
                    new_values,
                )
                with Session(self._engine) as session:
                    registered = self._register_blobs(new_values, session)
                blob_ids.update(registered)
                # Only the values stored here: a blob found in the registry
                # may lack its object, which reads have to find out.
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
            The cached values by blob ID, which never needed storage.
        """
        return self._cache.get_cached(blob_ids)

    def load(self, blob_ids: Collection[UUID]) -> Dict[UUID, str]:
        """Load the values held by blobs.

        Reads the registry in a short session of its own and the backend
        outside of it, so the caller must not hold a transaction either.

        Args:
            blob_ids: The blobs to load.

        Returns:
            The values by blob ID.
        """
        return self._cache.get_or_load(blob_ids, self._load_uncached_payloads)

    def _get_registered_blob_ids(
        self, sha256s: Collection[str], session: Session
    ) -> Dict[str, UUID]:
        """Get the registered blobs of contents.

        Args:
            sha256s: The SHA-256 of the contents.
            session: The session to use.

        Returns:
            The IDs of the registered blobs by SHA-256.
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
        """Create the registry row of a payload value.

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
            The IDs of the registered blobs by SHA-256.
        """
        # Sorted, so that concurrent writers lock the same keys in the same
        # order and never deadlock each other.
        values = sorted(values, key=lambda value: value.sha256)
        blobs = [self._build_blob_record(value) for value in values]
        # Read before the commit expires the rows, which would reload each.
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
            # Read before the commit expires the row, which would reload it.
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
        self, blob_ids: Collection[UUID]
    ) -> Dict[UUID, str]:
        """Read blobs from the backend.

        Args:
            blob_ids: The blobs to read.

        Returns:
            The values by blob ID.

        Raises:
            RuntimeError: If a blob is not registered.
            NonRetryablePayloadStorageError: If a blob is stored at another location than
                the configured one.
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

        sha256s = sorted({blob.sha256 for blob in blobs})
        data = dict(
            zip(sha256s, self._call_backend_batch(backend.get, sha256s))
        )
        return {
            blob.id: self._verify_and_decode(blob, data[blob.sha256])
            for blob in blobs
        }

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
                f"location `{blob.location_fingerprint}` do not match its registered "
                "size and SHA-256."
            )
        return data.decode("utf-8")

    def _call_backend_batch(
        self, function: Callable[[T], R], items: Sequence[T]
    ) -> List[R]:
        """Call the backend for several items concurrently.

        Args:
            function: The backend call.
            items: The items to call it for.

        Returns:
            The results, in the order of the items.

        Raises:
            PayloadStorageUnavailableError: If a call fails or does not
                return in time, or calls to the backend are paused after it
                failed repeatedly.
            NonRetryablePayloadStorageError: If the storage refuses a call in a way that
                retrying does not fix, such as a missing object or denied
                access.
        """
        futures, stalled = self._run_backend_calls(function, items)
        # The first in item order, so that the same failures always give
        # the same error.
        error = next(
            (
                error
                for future in futures
                if future.done()
                and not future.cancelled()
                and (error := future.exception())
            ),
            None,
        )
        if error is None and not stalled:
            return [future.result() for future in futures]
        if isinstance(error, PayloadStorageUnavailableError):
            # Calls to the backend are paused; the breaker logged why.
            raise PayloadStorageUnavailableError(str(error)) from error

        logger.warning(
            "Execution payload storage failed in a batch of %d calls: %s",
            len(items),
            error or f"no call returned within {self._timeout} seconds",
        )
        if isinstance(error, (FileNotFoundError, PermissionError)):
            # Retrying brings back neither a missing object nor access, so
            # these fail at once instead of as a retried 503.
            raise NonRetryablePayloadStorageError(
                f"Execution payload storage refused the request: {error}"
            ) from error
        if error:
            raise PayloadStorageUnavailableError(
                f"Execution payload storage failed: {error}"
            ) from error
        raise PayloadStorageUnavailableError(
            "Execution payload storage did not respond within "
            f"{self._timeout} seconds."
        )

    def _call_guarded(self, function: Callable[[T], R], item: T) -> R:
        """Make one backend call through the circuit breaker.

        The breaker counts single calls, so that one slow or missing object
        among healthy calls never pauses the backend.

        Args:
            function: The backend call.
            item: The item to call it for.

        Returns:
            The result of the call.
        """
        assert self._breaker
        with self._breaker.guard():
            return function(item)

    def _run_backend_calls(
        self, function: Callable[[T], R], items: Sequence[T]
    ) -> Tuple[List["Future[R]"], bool]:
        """Run backend calls on the shared threads until they end or stall.

        The threads are shared by every request of the process. A batch keeps
        at most one call per thread submitted, and submits the next one as a
        call returns, so that the calls of other requests queue behind at most
        one round of its calls instead of all of them.

        The calls stall once none of them returns for a whole timeout plus a
        margin, which stalled storage causes within about one timeout. A
        deadline for the whole batch would instead fail healthy storage that
        is busy. The first failure or a stall cancels the calls still queued.

        Args:
            function: The backend call.
            items: The items to call it for.

        Returns:
            The submitted calls in item order, which are all done unless one
            failed or they stalled, and whether they stalled.
        """
        futures: List["Future[R]"] = []
        pending: Set["Future[R]"] = set()
        stalled = False
        while pending or len(futures) < len(items):
            while (
                len(futures) < len(items)
                and len(pending) < MAX_CONCURRENT_BACKEND_CALLS
            ):
                future = self._executor.submit(
                    self._call_guarded, function, items[len(futures)]
                )
                futures.append(future)
                pending.add(future)
            done, pending = wait(
                pending,
                timeout=self._timeout + BACKEND_STALL_MARGIN_SECONDS,
                return_when=FIRST_COMPLETED,
            )
            stalled = not done
            if stalled or any(future.exception() for future in done):
                break
        for future in pending:
            future.cancel()
        return futures, stalled
