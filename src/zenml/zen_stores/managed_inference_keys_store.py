"""Recoverable handoff of managed inference keys to the secrets store."""

import hashlib
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import CursorResult, true, update
from sqlmodel import Session, col

from zenml.exceptions import IllegalOperationError
from zenml.models import SecretRequest
from zenml.models.managed_model import ManagedModelInferenceSecret
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.managed_model_schemas import (
    ManagedModelOperationSchema,
    ManagedModelServiceSchema,
)
from zenml.zen_stores.schemas.secret_schemas import SecretSchema

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStore


class _CredentialJournal(BaseModel):
    """Non-secret ownership records retained until service purging."""

    version: int = 0
    initialized: bool = False
    active: Optional[ManagedModelInferenceSecret] = None
    owned: list[UUID] = Field(default_factory=list)


class ManagedInferenceKeysStore:
    """Persist secret values before publishing their hash and reference."""

    def __init__(self, store: "SqlZenStore") -> None:
        """Bind the credential coordinator to the workspace.

        Args:
            store: Workspace with the configured primary and backup secrets stores.
        """
        self.store = store

    def ensure(self, service_id: UUID, user_id: UUID) -> None:
        """Initialize credentials once; creation retries never rotate a key.

        Args:
            service_id: Accepted managed service.
            user_id: Authenticated creator of the private secret.
        """
        with Session(self.store.engine) as session:
            row = self._get_row(session, service_id)
            journal = _CredentialJournal.model_validate_json(
                row.inference_credentials
            )
            if journal.initialized:
                return
            version = journal.version
        self.rotate(service_id, user_id, expected_version=version)

    def rotate(
        self,
        service_id: UUID,
        user_id: UUID,
        expected_version: Optional[int] = None,
    ) -> ManagedModelInferenceSecret:
        """Store a new immutable secret before switching inference admission.

        Args:
            service_id: Service whose key is replaced.
            user_id: Authenticated owner of the new private secret.
            expected_version: Observed version for initial-creation retries.

        Returns:
            Reference to the stored key; never the plaintext value.

        Raises:
            IllegalOperationError: If deletion, revocation or another rotation wins.
            KeyError: If the service no longer exists.
            RuntimeError: If secret storage fails; the previous key remains active.
        """
        key = "zmm_" + secrets.token_urlsafe(32)
        secret_id = uuid4()
        reference = ManagedModelInferenceSecret(
            id=secret_id,
            name=f"managed-model-{service_id}-{secret_id.hex}",
        )
        with Session(self.store.engine) as session:
            row = self._get_row(session, service_id)
            original = row.inference_credentials
            journal = _CredentialJournal.model_validate_json(original)
            if row.to_model().desired_state == "deleted":
                raise IllegalOperationError(
                    "Cannot issue a key for a deleted service."
                )
            if (
                expected_version is not None
                and journal.version != expected_version
            ):
                raise IllegalOperationError(
                    "Inference credentials changed; retry the request."
                )
            journal.version += 1
            journal.owned.append(secret_id)
            version = journal.version
            # Reserve ownership and secret metadata atomically. A crash during
            # external storage still leaves a discoverable cleanup record.
            metadata = SecretSchema.from_request(
                SecretRequest(name=reference.name, private=True, user=user_id)
            )
            metadata.id = secret_id
            session.add(metadata)
            self._save(
                session,
                service_id,
                original,
                journal,
                expected_generation=row.generation,
            )
            session.commit()

        # A separate secret per attempt prevents a late write from overwriting
        # the working credential. Failure here leaves the previous key active.
        try:
            self.store._set_secret_values(secret_id, {"api_key": key})
        except Exception:
            # Backend errors may include request contents. Keep API diagnostics
            # fixed and preserve the owned ID for retryable cleanup.
            raise RuntimeError(
                "Unable to store the inference key; retry the original request."
            ) from None
        try:
            with Session(self.store.engine) as session:
                row = self._get_row(session, service_id)
                original = row.inference_credentials
                journal = _CredentialJournal.model_validate_json(original)
                if (
                    journal.version != version
                    or row.to_model().desired_state == "deleted"
                ):
                    raise IllegalOperationError(
                        "Inference credentials changed; retry the request."
                    )
                journal.initialized = True
                journal.active = reference
                self._save(
                    session,
                    service_id,
                    original,
                    journal,
                    expected_generation=row.generation,
                    inference_key_hash=hashlib.sha256(
                        key.encode()
                    ).hexdigest(),
                )
                # Public creation is held until its key is durably retrievable.
                session.exec(
                    update(ManagedModelOperationSchema)
                    .where(
                        col(ManagedModelOperationSchema.service_id)
                        == service_id,
                        col(ManagedModelOperationSchema.action) == "create",
                        col(ManagedModelOperationSchema.status) == "pending",
                        col(ManagedModelOperationSchema.available_at)
                        == datetime(9999, 1, 1),
                    )
                    .values(available_at=None)
                )
                session.commit()
        except (KeyError, IllegalOperationError):
            # A newer intent won. A late backend write must not leave a key
            # behind after service deletion or publish an obsolete reference.
            self._delete_owned_secret(secret_id)
            raise
        return reference

    def revoke(self, service_id: UUID) -> None:
        """Invalidate admission and fence any in-flight credential issuance.

        Args:
            service_id: Service whose key is revoked.
        """
        with Session(self.store.engine) as session:
            row = self._get_row(session, service_id)
            journal = _CredentialJournal.model_validate_json(
                row.inference_credentials
            )
            journal.version += 1
            journal.initialized = True
            journal.active = None
            self._save(
                session,
                service_id,
                row.inference_credentials,
                journal,
                inference_key_hash=None,
            )
            session.commit()

    def cleanup(self, service_id: UUID) -> None:
        """Remove owned secrets while finishing deletion or purging its tombstone.

        Ownership records survive partial cleanup so the operation can be retried.
        This includes retired keys and interrupted issuance attempts.

        Args:
            service_id: Service with accepted deletion intent.

        Raises:
            IllegalOperationError: If service deletion has not been requested.
        """
        with Session(self.store.engine) as session:
            row = self._get_row(session, service_id)
            service = row.to_model()
            if service.desired_state != "deleted":
                raise IllegalOperationError(
                    "Request service deletion before secret cleanup."
                )
            journal = _CredentialJournal.model_validate_json(
                row.inference_credentials
            )
            journal.version += 1
            journal.initialized = True
            journal.active = None
            self._save(
                session,
                service_id,
                row.inference_credentials,
                journal,
                inference_key_hash=None,
            )
            session.commit()
        for secret_id in journal.owned:
            self._delete_owned_secret(secret_id)

    def _delete_owned_secret(self, secret_id: UUID) -> None:
        # Values can exist even if someone removed metadata manually.
        try:
            self.store._delete_secret_values(secret_id)
        except KeyError:
            pass
        with Session(self.store.engine) as session:
            metadata = session.get(SecretSchema, secret_id)
            if metadata is not None:
                session.delete(metadata)
                session.commit()

    @staticmethod
    def _get_row(
        session: Session, service_id: UUID
    ) -> ManagedModelServiceSchema:
        row = session.get(ManagedModelServiceSchema, service_id)
        if row is None:
            raise KeyError(f"Managed model service {service_id} not found.")
        return row

    @staticmethod
    def _save(
        session: Session,
        service_id: UUID,
        original: str,
        journal: _CredentialJournal,
        expected_generation: Optional[int] = None,
        **values: object,
    ) -> None:
        result = session.execute(
            update(ManagedModelServiceSchema)
            .where(
                col(ManagedModelServiceSchema.id) == service_id,
                col(ManagedModelServiceSchema.inference_credentials)
                == original,
            )
            .where(
                col(ManagedModelServiceSchema.generation)
                == expected_generation
                if expected_generation is not None
                else true()
            )
            .values(
                inference_credentials=journal.model_dump_json(),
                updated=utc_now(),
                **values,
            )
        )
        if cast(CursorResult[Any], result).rowcount != 1:
            raise IllegalOperationError(
                "Inference credentials changed; retry the request."
            )
