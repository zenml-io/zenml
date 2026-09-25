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
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, wait
from typing import (
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
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
    PayloadIntegrityError,
    PayloadStorageError,
    PayloadStorageUnavailableError,
)
from zenml.zen_stores.payload_storage.backends import (
    PayloadBackend,
    create_payload_backend,
)
from zenml.zen_stores.payload_storage.cache import PayloadCache
from zenml.zen_stores.payload_storage.config import (
    PayloadStorageConfiguration,
)
from zenml.zen_stores.payload_storage.payloads import (
    PayloadSchema,
    PayloadValue,
)
from zenml.zen_stores.schemas.blob_schemas import BlobSchema

IDENTITY_CODEC = "identity"
MAX_CONCURRENT_BACKEND_CALLS = 32
# Bounds the size of the `IN` lists of registry queries.
QUERY_BATCH_SIZE = 500

# A blob is registered once per content and media type.
BlobKey = Tuple[str, str]

T = TypeVar("T")
R = TypeVar("R")


def _get_blob_key(value: PayloadValue) -> BlobKey:
    """Get the registry key of a payload value.

    Args:
        value: The payload value.

    Returns:
        The key.
    """
    return value.sha256, value.media_type.value


def _batched(items: Collection[T]) -> Iterable[List[T]]:
    """Split items into batches for `IN` lists.

    Args:
        items: The items to split.

    Yields:
        The batches.
    """
    batch = list(items)
    for start in range(0, len(batch), QUERY_BATCH_SIZE):
        yield batch[start : start + QUERY_BATCH_SIZE]


class OffloadedPayloads:
    """Payload values offloaded ahead of the transaction referencing them."""

    def __init__(
        self, blob_ids: Dict[Tuple[str, str], UUID], enabled: bool = True
    ) -> None:
        """Initializes the offloaded payloads.

        Args:
            blob_ids: The blobs holding the offloaded values, by value and
                media type.
            enabled: Whether offloading is enabled. If not, schemas keep
                their payloads inline.
        """
        self._blob_ids = blob_ids
        self._enabled = enabled

    @classmethod
    def disabled(cls) -> "OffloadedPayloads":
        """Payloads of a store that keeps payloads inline.

        Returns:
            Offloaded payloads that leave schemas unchanged.
        """
        return cls(blob_ids={}, enabled=False)

    @property
    def values(self) -> Dict[UUID, str]:
        """The offloaded values by the blob that holds them.

        Returns:
            The offloaded values.
        """
        return {blob_id: text for (text, _), blob_id in self._blob_ids.items()}

    def reference(self, *schemas: PayloadSchema) -> None:
        """Replace the inline payload values of schemas by their blobs.

        Args:
            *schemas: The schemas to update.

        Raises:
            RuntimeError: If a schema holds a value that was not offloaded.
        """
        if not self._enabled:
            return
        for schema in schemas:
            for field in schema.PAYLOAD_FIELDS:
                text = field.get_inline_text(schema)
                if text is None:
                    continue
                blob_id = self._blob_ids.get((text, field.media_type.value))
                if blob_id is None:
                    raise RuntimeError(
                        f"The `{field.name}` payload of a "
                        f"`{type(schema).__name__}` was not offloaded."
                    )
                field.set_blob_id(schema, blob_id)


class PayloadStore:
    """Offloads the payloads of execution schemas and resolves them.

    Payloads are stored as content-addressed blobs in object storage: each
    distinct value is stored once, in the backend that was the write backend
    when the value was first offloaded. The `blob` table registers every blob, and a blob is only
    registered once its bytes are durable, so that a reference never points to
    missing bytes.
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
        # The backend receiving new payloads; None keeps them inline.
        self._write_backend = (
            config.write_backend if config.offload_enabled else None
        )
        # Keyed by the name stored in `blob.stored_in`.
        self._backends: Dict[str, PayloadBackend] = {
            backend_type.value: create_payload_backend(
                backend_type, configuration, timeout=config.timeout
            )
            for backend_type, configuration in config.backends.items()
        }
        self._cache = PayloadCache(max_size=config.cache_size)
        self._timeout = config.timeout
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_BACKEND_CALLS,
            thread_name_prefix="zenml-payload-storage",
        )

    @property
    def has_backends(self) -> bool:
        """Whether any backend is configured, so that blobs can exist.

        Returns:
            Whether any backend is configured.
        """
        return bool(self._backends)

    def verify_backends(self) -> None:
        """Verify that every backend holding blobs is configured.

        Raises:
            RuntimeError: If blobs are held by a backend that is not
                configured.
        """
        if not inspect(self._engine).has_table(BlobSchema.__tablename__):
            return

        # Compared with the stored names rather than the known ones, so that
        # blobs of a backend added by a newer release are found as well.
        configured = list(self._backends)
        with Session(self._engine) as session:
            stored_in = session.exec(
                select(BlobSchema.stored_in)
                .where(col(BlobSchema.stored_in).not_in(configured))
                .limit(1)
            ).first()
        if stored_in:
            raise RuntimeError(
                f"Execution payloads are stored in the `{stored_in}` payload "
                "backend, which is not configured. Configure it in the "
                "`backends` of the payload storage configuration of the "
                "store."
            )

    def offload(self, values: Iterable[PayloadValue]) -> OffloadedPayloads:
        """Store payload values ahead of the transaction referencing them.

        The bytes of new values are stored in the write backend first. Their
        blobs are then registered in a short transaction of their own. If the
        transaction referencing them fails afterwards, the unreferenced blobs
        are reused by the next write of the same content. No transaction may
        be open while this runs, since it waits for the backend.

        Args:
            values: The values to offload.

        Returns:
            The offloaded payloads, which reference the blobs from schemas.
        """
        if self._write_backend is None:
            return OffloadedPayloads.disabled()

        values_by_key = {_get_blob_key(value): value for value in values}
        blob_ids: Dict[BlobKey, UUID] = {}
        if values_by_key:
            backend = self._backends[self._write_backend.value]
            with Session(self._engine) as session:
                blob_ids = self._get_registered_blobs(
                    values_by_key, session=session
                )
            new_values = [
                value
                for key, value in values_by_key.items()
                if key not in blob_ids
            ]
            if new_values:
                unique_values = {v.sha256: v for v in new_values}.values()
                self._call_backend(
                    lambda value: backend.put(value.sha256, value.data),
                    list(unique_values),
                )
                with Session(self._engine) as session:
                    blob_ids.update(self._register(new_values, session))

        for key, blob_id in blob_ids.items():
            self._cache.put(blob_id, values_by_key[key].text)
        return OffloadedPayloads(
            blob_ids={
                (values_by_key[key].text, key[1]): blob_id
                for key, blob_id in blob_ids.items()
            }
        )

    def load(self, blob_ids: Collection[UUID]) -> Dict[UUID, str]:
        """Load the values held by blobs.

        Reads the registry in a short session of its own and the backends
        outside of it, so the caller must not hold a transaction either.

        Args:
            blob_ids: The blobs to load.

        Returns:
            The values by blob ID.
        """
        return self._cache.get_many(blob_ids, self._read)

    def _get_registered_blobs(
        self, values_by_key: Dict[BlobKey, PayloadValue], session: Session
    ) -> Dict[BlobKey, UUID]:
        """Get the registered blobs of payload values.

        Args:
            values_by_key: The payload values by registry key.
            session: The session to use.

        Returns:
            The IDs of the blobs registered for the values.
        """
        blob_ids: Dict[BlobKey, UUID] = {}
        for sha256s in _batched({sha256 for sha256, _ in values_by_key}):
            for blob_id, sha256, media_type in session.exec(
                select(
                    BlobSchema.id, BlobSchema.sha256, BlobSchema.media_type
                ).where(col(BlobSchema.sha256).in_(sha256s))
            ):
                if (sha256, media_type) in values_by_key:
                    blob_ids[(sha256, media_type)] = blob_id
        return blob_ids

    def _create_blob(self, value: PayloadValue) -> BlobSchema:
        """Create the registry row of a payload value.

        Args:
            value: The payload value.

        Returns:
            The registry row.
        """
        assert self._write_backend
        return BlobSchema(
            sha256=value.sha256,
            media_type=value.media_type.value,
            codec=IDENTITY_CODEC,
            size=len(value.data),
            stored_in=self._write_backend.value,
        )

    def _register(
        self, values: List[PayloadValue], session: Session
    ) -> Dict[BlobKey, UUID]:
        """Register the blobs of payload values whose bytes are durable.

        Args:
            values: The payload values.
            session: The session to register them with.

        Returns:
            The IDs of the registered blobs.
        """
        # Sorted, so that concurrent writers lock the same keys in the same
        # order and never deadlock each other.
        values = sorted(values, key=_get_blob_key)
        blobs = [self._create_blob(value) for value in values]
        session.add_all(blobs)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            # A concurrent writer registered some of the same content first.
            return {
                _get_blob_key(value): self._get_or_register(value)
                for value in values
            }
        return {
            _get_blob_key(value): blob.id for value, blob in zip(values, blobs)
        }

    def _get_or_register(self, value: PayloadValue) -> UUID:
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
            blob = self._create_blob(value)
            session.add(blob)
            try:
                session.commit()
                return blob.id
            except IntegrityError:
                session.rollback()
                # The rollback ended the transaction, so this read sees the
                # blob registered by the concurrent writer.
                existing = session.exec(
                    select(BlobSchema.id).where(
                        BlobSchema.sha256 == value.sha256,
                        BlobSchema.media_type == value.media_type.value,
                    )
                ).first()
                if existing is None:
                    raise
                return existing

    def _read(self, blob_ids: Collection[UUID]) -> Dict[UUID, str]:
        """Read blobs from their backends.

        Args:
            blob_ids: The blobs to read.

        Returns:
            The values by blob ID.

        Raises:
            RuntimeError: If a blob is not registered.
            PayloadStorageError: If a blob is held by a backend that is not
                configured.
        """
        blobs: List[BlobSchema] = []
        with Session(self._engine) as session:
            for batch in _batched(blob_ids):
                blobs.extend(
                    session.exec(
                        select(BlobSchema).where(col(BlobSchema.id).in_(batch))
                    )
                )
        if missing := set(blob_ids) - {blob.id for blob in blobs}:
            raise RuntimeError(
                f"Payload blobs {sorted(str(blob_id) for blob_id in missing)} "
                "are referenced but not registered."
            )

        # The same bytes can be stored in several backends, for example under
        # two media types after a backend switch, so each object is checked
        # against the bytes of its own backend.
        data: Dict[Tuple[str, str], bytes] = {}
        sha256s_by_backend: Dict[str, Set[str]] = defaultdict(set)
        for blob in blobs:
            sha256s_by_backend[blob.stored_in].add(blob.sha256)
        for stored_in, sha256s in sha256s_by_backend.items():
            backend = self._backends.get(stored_in)
            if backend is None:
                raise PayloadStorageError(
                    f"Execution payloads are stored in the `{stored_in}` "
                    "payload backend, which is not configured."
                )
            ordered = sorted(sha256s)
            for sha256, content in zip(
                ordered, self._call_backend(backend.get, ordered)
            ):
                data[(stored_in, sha256)] = content
        return {
            blob.id: self._decode(blob, data[(blob.stored_in, blob.sha256)])
            for blob in blobs
        }

    @staticmethod
    def _decode(blob: BlobSchema, data: bytes) -> str:
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
            len(data) != blob.size
            or hashlib.sha256(data).hexdigest() != blob.sha256
        ):
            raise PayloadIntegrityError(
                f"The bytes of payload blob `{blob.id}` in the "
                f"`{blob.stored_in}` payload backend do not match its "
                "registered size and SHA-256."
            )
        return data.decode("utf-8")

    def _call_backend(
        self, function: Callable[[T], R], items: Sequence[T]
    ) -> List[R]:
        """Call a backend for several items concurrently.

        Args:
            function: The backend call.
            items: The items to call it for.

        Returns:
            The results, in the order of the items.

        Raises:
            PayloadStorageUnavailableError: If a call fails or does not
                return in time.
            PayloadStorageError: If the storage refuses a call in a way that
                retrying does not fix, such as a missing object or denied
                access.
        """
        futures = [self._executor.submit(function, item) for item in items]
        _, pending = wait(futures, timeout=self._timeout)
        if pending:
            for future in pending:
                future.cancel()
            raise PayloadStorageUnavailableError(
                "Execution payload storage did not respond within "
                f"{self._timeout} seconds."
            )
        try:
            return [future.result() for future in futures]
        except (FileNotFoundError, PermissionError) as e:
            # Retrying brings back neither a missing object nor access, so
            # these fail at once instead of as a retried 503.
            raise PayloadStorageError(
                f"Execution payload storage refused the request: {e}"
            ) from e
        except Exception as e:
            raise PayloadStorageUnavailableError(
                f"Execution payload storage failed: {e}"
            ) from e
