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
"""Session manager for orchestrating session lifecycle."""

import json
from typing import Any, Dict, Optional
from uuid import uuid4

from zenml.deployers.server.session import Session, SessionBackend
from zenml.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """High-level orchestrator for session lifecycle management.

    Handles session resolution (get-or-create), state persistence with
    size limits, and cleanup coordination.

    Attributes:
        backend: The storage backend for sessions.
        ttl_seconds: Default TTL for new sessions (None = no expiry).
        max_state_bytes: Optional maximum size for session state in bytes.
    """

    def __init__(
        self,
        backend: SessionBackend,
        ttl_seconds: Optional[int] = None,
        max_state_bytes: Optional[int] = None,
    ) -> None:
        """Initialize the session manager.

        Args:
            backend: Storage backend for sessions.
            ttl_seconds: Default session TTL in seconds (None = no expiry).
            max_state_bytes: Optional maximum state size in bytes.
        """
        self.backend = backend
        self.ttl_seconds = ttl_seconds
        self.max_state_bytes = max_state_bytes
        self._logger = logger

    def resolve(
        self,
        requested_id: Optional[str],
        deployment_id: str,
        pipeline_id: Optional[str] = None,
    ) -> Session:
        """Resolve a session by ID or create a new one.

        If requested_id is provided, attempts to load the existing session.
        If not found or expired, creates a new session with that ID.
        If requested_id is None, generates a new ID and creates a session.

        Args:
            requested_id: Optional session ID to resume.
            deployment_id: The deployment identifier.
            pipeline_id: Optional pipeline identifier.

        Returns:
            The resolved or newly created session.
        """
        session_id = requested_id or uuid4().hex

        if requested_id:
            session = self.backend.load(session_id, deployment_id)
            if session:
                session.touch(self.ttl_seconds)
                self.backend.update(
                    session_id,
                    deployment_id,
                    session.state,
                    ttl_seconds=self.ttl_seconds,
                )
                self._logger.debug(
                    f"Resolved existing session [session_id={session_id}] "
                    f"[deployment_id={deployment_id}]"
                )
                return session

        session = self.backend.create(
            session_id=session_id,
            deployment_id=deployment_id,
            pipeline_id=pipeline_id,
            initial_state={},
            ttl_seconds=self.ttl_seconds,
        )

        self._logger.info(
            f"Created new session [session_id={session_id}] "
            f"[deployment_id={deployment_id}]"
        )

        return session

    def persist_state(
        self,
        session: Session,
        new_state: Dict[str, Any],
    ) -> Session:
        """Persist updated state to the backend with size validation.

        Args:
            session: The session to update.
            new_state: New state dictionary to persist.

        Returns:
            The updated session from the backend.
        """
        if self.max_state_bytes is not None:
            self._ensure_size_within_limit(new_state)

        updated_session = self.backend.update(
            session_id=session.id,
            deployment_id=session.deployment_id,
            state=new_state,
            ttl_seconds=self.ttl_seconds,
        )

        self._logger.debug(
            f"Persisted state [session_id={session.id}] "
            f"[deployment_id={session.deployment_id}]"
        )

        return updated_session

    def delete_session(self, session: Session) -> None:
        """Delete a session from the backend.

        Args:
            session: The session to delete.
        """
        self.backend.delete(session.id, session.deployment_id)

    def _ensure_size_within_limit(self, state: Dict[str, Any]) -> None:
        """Validate that state size is within configured limit.

        Args:
            state: The state dictionary to validate.

        Raises:
            ValueError: If state exceeds max_state_bytes.
        """
        if self.max_state_bytes is None:
            return

        try:
            state_json = json.dumps(state, ensure_ascii=False)
            state_bytes = len(state_json.encode("utf-8"))
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Session state must be JSON-serializable: {e}"
            ) from e

        if state_bytes > self.max_state_bytes:
            raise ValueError(
                f"Session state size ({state_bytes} bytes) exceeds "
                f"maximum allowed ({self.max_state_bytes} bytes)"
            )
