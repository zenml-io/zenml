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
"""In-memory session backend implementation."""

import threading
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

from pydantic import Field

from zenml.deployers.server.session import (
    BaseBackendConfig,
    Session,
    SessionBackend,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class InMemoryBackendConfig(BaseBackendConfig):
    """Configuration for in-memory session backend.

    Attributes:
        max_sessions: Maximum number of sessions to store. When exceeded,
            least-recently-used sessions are evicted. None means unlimited.
    """

    max_sessions: Optional[int] = Field(
        default=10_000,
        description="Maximum number of sessions (LRU eviction when exceeded)",
    )


class InMemorySessionBackend(SessionBackend):
    """Thread-safe in-memory session storage with LRU eviction.

    Uses an OrderedDict to track access order for LRU eviction when
    max_sessions is exceeded. All operations are guarded by a reentrant lock.

    Attributes:
        config: Backend configuration.
    """

    def __init__(self, config: InMemoryBackendConfig) -> None:
        """Initialize the in-memory backend.

        Args:
            config: Configuration for the backend.
        """
        self.config = config
        self._sessions: OrderedDict[Tuple[str, str], Session] = OrderedDict()
        self._lock = threading.RLock()

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

            if session.is_expired():
                logger.debug(
                    f"Session expired on load [session_id={session_id}] "
                    f"[deployment_id={deployment_id}]"
                )
                del self._sessions[key]
                return None

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

            session = Session(
                id=session_id,
                deployment_id=deployment_id,
                pipeline_id=pipeline_id,
                state=initial_state or {},
            )

            if ttl_seconds is not None:
                session.touch(ttl_seconds)

            self._sessions[key] = session
            self._sessions.move_to_end(key)

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

            session.state = dict(state)

            session.touch(ttl_seconds)

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
        if self.config.max_sessions is None:
            return

        while len(self._sessions) > self.config.max_sessions:
            evicted_key, evicted_session = self._sessions.popitem(last=False)
            logger.warning(
                f"Evicted LRU session [session_id={evicted_session.id}] "
                f"[deployment_id={evicted_session.deployment_id}] "
                f"due to capacity limit ({self.config.max_sessions})"
            )
