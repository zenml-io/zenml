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
"""Deployment-scoped session infrastructure.

This module provides server-managed session storage to enable stateful
interactions across multiple deployment invocations. Sessions are scoped
to deployments and support TTL-based expiration, thread-safe concurrent
access, and optional size limits.

Key components:
- Session: Pydantic model representing session data and metadata
- SessionBackend: Abstract interface for session storage
- InMemorySessionBackend: Thread-safe in-memory implementation with LRU eviction
- SessionManager: High-level orchestrator for session lifecycle management

Assumptions:
- Last-write-wins semantics for concurrent updates to the same session
- Sessions are deployment-scoped; different deployments have isolated namespaces
- Expiration is lazy (checked on access) plus periodic cleanup via backend.cleanup()
"""

import json
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from zenml.logger import get_logger

logger = get_logger(__name__)


class Session(BaseModel):
    """Represents a deployment session with state and metadata.

    Attributes:
        id: Unique session identifier (hex string).
        deployment_id: ID of the deployment this session belongs to.
        pipeline_id: Optional ID of the pipeline associated with this session.
        state: Arbitrary JSON-serializable state dictionary.
        created_at: Timestamp when the session was created (UTC).
        updated_at: Timestamp when the session was last accessed/modified (UTC).
        expires_at: Optional expiration timestamp (UTC); None means no expiry.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    deployment_id: str
    pipeline_id: Optional[str] = None
    state: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: Optional[datetime] = None

    def touch(self, ttl_seconds: Optional[int] = None) -> None:
        """Update access timestamp and optionally extend expiration.

        Args:
            ttl_seconds: If provided, set expires_at to now + ttl_seconds.
                If None and expires_at is already set, leave it unchanged.
        """
        now = datetime.now(timezone.utc)
        self.updated_at = now

        if ttl_seconds is not None:
            self.expires_at = now + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        """Check if the session has expired.

        Returns:
            True if expires_at is set and in the past, False otherwise.
        """
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class SessionBackend(ABC):
    """Abstract interface for session storage backends."""

    @abstractmethod
    def load(self, session_id: str, deployment_id: str) -> Optional[Session]:
        """Load a session by ID within a deployment scope.

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.

        Returns:
            The session if found and not expired, None otherwise.
        """

    @abstractmethod
    def create(
        self,
        session_id: str,
        deployment_id: str,
        pipeline_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Session:
        """Create a new session.

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.
            pipeline_id: Optional pipeline identifier.
            initial_state: Optional initial state dictionary.
            ttl_seconds: Optional TTL in seconds; if provided, sets expires_at.

        Returns:
            The created session.

        Raises:
            ValueError: If a session with the same ID already exists.
        """

    @abstractmethod
    def update(
        self,
        session_id: str,
        deployment_id: str,
        state: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> Session:
        """Update an existing session's state.

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.
            state: New state dictionary (replaces existing state).
            ttl_seconds: Optional TTL to refresh expiration.

        Returns:
            The updated session.

        Raises:
            KeyError: If the session does not exist.
        """

    @abstractmethod
    def delete(self, session_id: str, deployment_id: str) -> None:
        """Delete a session.

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.
        """

    @abstractmethod
    def cleanup(self) -> int:
        """Remove all expired sessions across all deployments.

        Returns:
            Number of sessions removed.
        """


class InMemorySessionBackend(SessionBackend):
    """Thread-safe in-memory session storage with LRU eviction.

    Uses an OrderedDict to track access order for LRU eviction when
    max_sessions is exceeded. All operations are guarded by a reentrant lock.

    Attributes:
        max_sessions: Optional maximum number of sessions to store. When
            exceeded, least-recently-used sessions are evicted.
    """

    def __init__(self, max_sessions: Optional[int] = None) -> None:
        """Initialize the in-memory backend.

        Args:
            max_sessions: Optional capacity limit; None means unlimited.
        """
        self._sessions: OrderedDict[Tuple[str, str], Session] = OrderedDict()
        self._lock = threading.RLock()
        self.max_sessions = max_sessions

    def load(self, session_id: str, deployment_id: str) -> Optional[Session]:
        """Load a session, performing lazy expiration removal.

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.

        Returns:
            Deep copy of the session if found and valid, None otherwise.
        """
        with self._lock:
            key = (deployment_id, session_id)
            session = self._sessions.get(key)

            if session is None:
                return None

            # Lazy expiration check
            if session.is_expired():
                logger.debug(
                    f"Session expired on load [session_id={session_id}] "
                    f"[deployment_id={deployment_id}]"
                )
                del self._sessions[key]
                return None

            # Move to end (mark as recently used)
            self._sessions.move_to_end(key)

            return session.model_copy(deep=True)

    def create(
        self,
        session_id: str,
        deployment_id: str,
        pipeline_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Session:
        """Create a new session with optional TTL.

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.
            pipeline_id: Optional pipeline identifier.
            initial_state: Optional initial state dictionary.
            ttl_seconds: Optional TTL in seconds.

        Returns:
            Deep copy of the created session.

        Raises:
            ValueError: If a session with the same ID already exists.
        """
        with self._lock:
            key = (deployment_id, session_id)

            if key in self._sessions:
                raise ValueError(
                    f"Session already exists [session_id={session_id}] "
                    f"[deployment_id={deployment_id}]"
                )

            # Create new session
            session = Session(
                id=session_id,
                deployment_id=deployment_id,
                pipeline_id=pipeline_id,
                state=initial_state or {},
            )

            # Set expiration if TTL provided
            if ttl_seconds is not None:
                session.touch(ttl_seconds)

            # Store and mark as recently used
            self._sessions[key] = session
            self._sessions.move_to_end(key)

            # Enforce capacity limit via LRU eviction
            self._evict_if_needed()

            logger.info(
                f"Created session [session_id={session_id}] "
                f"[deployment_id={deployment_id}] "
                f"[ttl_seconds={ttl_seconds}]"
            )

            return session.model_copy(deep=True)

    def update(
        self,
        session_id: str,
        deployment_id: str,
        state: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> Session:
        """Update session state and refresh timestamps.

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.
            state: New state dictionary (replaces existing).
            ttl_seconds: Optional TTL to refresh expiration.

        Returns:
            Deep copy of the updated session.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            key = (deployment_id, session_id)

            if key not in self._sessions:
                raise KeyError(
                    f"Session not found [session_id={session_id}] "
                    f"[deployment_id={deployment_id}]"
                )

            session = self._sessions[key]

            # Replace state with deep copy
            session.state = dict(state)

            # Refresh timestamps and optionally extend expiration
            session.touch(ttl_seconds)

            # Mark as recently used
            self._sessions.move_to_end(key)

            logger.debug(
                f"Updated session [session_id={session_id}] "
                f"[deployment_id={deployment_id}]"
            )

            return session.model_copy(deep=True)

    def delete(self, session_id: str, deployment_id: str) -> None:
        """Delete a session (silent if not found).

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.
        """
        with self._lock:
            key = (deployment_id, session_id)
            if key in self._sessions:
                del self._sessions[key]
                logger.info(
                    f"Deleted session [session_id={session_id}] "
                    f"[deployment_id={deployment_id}]"
                )

    def cleanup(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed.
        """
        with self._lock:
            expired_keys = [
                key
                for key, session in self._sessions.items()
                if session.is_expired()
            ]

            for key in expired_keys:
                del self._sessions[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired sessions")

            return len(expired_keys)

    def _evict_if_needed(self) -> None:
        """Evict least-recently-used sessions if capacity exceeded.

        Must be called while holding self._lock.
        """
        if self.max_sessions is None:
            return

        while len(self._sessions) > self.max_sessions:
            # Remove oldest (first) entry
            evicted_key, evicted_session = self._sessions.popitem(last=False)
            logger.warning(
                f"Evicted LRU session [session_id={evicted_session.id}] "
                f"[deployment_id={evicted_session.deployment_id}] "
                f"due to capacity limit ({self.max_sessions})"
            )


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

        # Attempt to load existing session
        if requested_id:
            session = self.backend.load(session_id, deployment_id)
            if session:
                # Refresh TTL on access
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

        # Create new session
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

        Raises:
            ValueError: If new_state exceeds max_state_bytes.
        """
        # Enforce size limit if configured
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

        # Serialize to JSON and measure byte size
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
