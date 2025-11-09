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
"""Session models and abstractions for deployment session management."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class BaseBackendConfig(BaseModel):
    """Base configuration shared by all session backends.

    This class doesn't define any fields itself but serves as the parent
    for all backend-specific configurations, enabling polymorphic config handling.
    """

    model_config = ConfigDict(extra="forbid")


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
