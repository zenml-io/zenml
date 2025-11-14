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
"""Local SQLite-based session backend implementation."""

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple, Union

from pydantic import Field

from zenml.deployers.server.session import (
    BaseBackendConfig,
    Session,
    SessionBackend,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class LocalBackendConfig(BaseBackendConfig):
    """Configuration for local SQLite session backend.

    Attributes:
        database_path: Custom path to SQLite database file. If not provided,
            defaults to <local_stores_path>/deployments/<deployment_id>/zenml_deployment_sessions.db
        journal_mode: SQLite journal mode (WAL recommended for concurrent access).
        synchronous: SQLite synchronous mode (NORMAL balances durability and performance).
        timeout: Connection timeout in seconds.
        max_retry_attempts: Maximum number of retry attempts for locked database.
        retry_base_delay: Base delay in seconds for exponential backoff retries.
    """

    database_path: Optional[str] = Field(
        default=None,
        description="Custom DB file path (optional)",
    )
    journal_mode: Literal["WAL", "DELETE"] = Field(
        default="WAL",
        description="SQLite journal mode",
    )
    synchronous: Literal["OFF", "NORMAL", "FULL"] = Field(
        default="NORMAL",
        description="SQLite synchronous mode",
    )
    timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="Connection timeout in seconds",
    )
    max_retry_attempts: int = Field(
        default=3,
        ge=1,
        description="Max retries for locked DB",
    )
    retry_base_delay: float = Field(
        default=0.05,
        ge=0.01,
        description="Base delay for retry backoff",
    )


# SQLite DDL for local backend
_CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    deployment_id TEXT NOT NULL,
    session_id    TEXT NOT NULL,
    pipeline_id   TEXT,
    state_json    TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    expires_at    TEXT,
    PRIMARY KEY (deployment_id, session_id)
)
"""

_CREATE_SESSIONS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_sessions_expires
    ON sessions (deployment_id, expires_at)
"""


class LocalSessionBackend(SessionBackend):
    """SQLite-based session storage shared by uvicorn workers on one host.

    This backend uses a local SQLite database file to persist sessions,
    enabling multiple uvicorn workers to share session state on the same
    host/VM. It uses WAL mode for concurrent access and provides the same
    semantics as the in-memory backend.

    Attributes:
        config: Backend configuration.
        db_path: Path to the SQLite database file (derived from config).
    """

    def __init__(
        self,
        config: LocalBackendConfig,
        db_path: Union[str, Path],
    ) -> None:
        """Initialize the local session backend.

        Args:
            config: Configuration for the backend.
            db_path: Path to the SQLite database file (overrides config.database_path if provided).
        """
        self.config = config
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,  # Manual transaction control
            timeout=self.config.timeout,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row

        with self._lock, self._conn:
            self._conn.execute(
                f"PRAGMA journal_mode={self.config.journal_mode}"
            )
            self._conn.execute(f"PRAGMA synchronous={self.config.synchronous}")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute(
                f"PRAGMA busy_timeout={int(self.config.timeout * 1000)}"
            )
            self._conn.execute(_CREATE_SESSIONS_TABLE)
            self._conn.execute(_CREATE_SESSIONS_INDEX)

        logger.info(
            f"Initialized local session backend [db_path={self.db_path}] "
            f"[journal_mode={self.config.journal_mode}] [synchronous={self.config.synchronous}]"
        )

    def __del__(self) -> None:
        """Close connection on cleanup."""
        try:
            self._conn.close()
        except Exception as e:
            logger.debug("Error closing connection: %s", e)

    def load(self, session_id: str, deployment_id: str) -> Optional[Session]:
        """Load a session, performing lazy expiration removal.

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.

        Returns:
            The session if found and not expired, None otherwise.
        """
        with self._lock, self._conn:
            row = self._conn.execute(
                """
                SELECT session_id, pipeline_id, state_json,
                       created_at, updated_at, expires_at
                  FROM sessions
                 WHERE deployment_id = ? AND session_id = ?
                """,
                (deployment_id, session_id),
            ).fetchone()

        if not row:
            return None

        session = self._row_to_session(row, deployment_id)

        # Lazy expiration check
        if session.is_expired():
            logger.debug(
                f"Session expired on load [session_id={session_id}] "
                f"[deployment_id={deployment_id}]"
            )
            self.delete(session_id, deployment_id)
            return None

        return session

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
            The created session.

        Raises:
            ValueError: If a session with the same ID already exists.
        """
        now = datetime.now(timezone.utc)
        state = initial_state or {}
        state_json = json.dumps(state, ensure_ascii=False)

        created_at = now.isoformat()
        updated_at = now.isoformat()
        expires_at = None
        if ttl_seconds is not None:
            expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()

        try:
            self._execute_with_retry(
                """
                INSERT INTO sessions (
                    deployment_id, session_id, pipeline_id,
                    state_json, created_at, updated_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deployment_id,
                    session_id,
                    pipeline_id,
                    state_json,
                    created_at,
                    updated_at,
                    expires_at,
                ),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError(
                f"Session already exists [session_id={session_id}] "
                f"[deployment_id={deployment_id}]"
            ) from e

        logger.info(
            f"Created session [session_id={session_id}] "
            f"[deployment_id={deployment_id}] "
            f"[ttl_seconds={ttl_seconds}]"
        )

        return Session(
            id=session_id,
            deployment_id=deployment_id,
            pipeline_id=pipeline_id,
            state=state,
            created_at=now,
            updated_at=now,
            expires_at=(now + timedelta(seconds=ttl_seconds))
            if ttl_seconds is not None
            else None,
        )

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
            The updated session.

        Raises:
            KeyError: If the session does not exist.
        """
        now = datetime.now(timezone.utc)
        state_json = json.dumps(state, ensure_ascii=False)
        updated_at = now.isoformat()

        expires_at = None
        if ttl_seconds is not None:
            expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()

        cursor = self._execute_with_retry(
            """
            UPDATE sessions
               SET state_json = ?,
                   updated_at = ?,
                   expires_at = COALESCE(?, expires_at)
             WHERE deployment_id = ? AND session_id = ?
            """,
            (state_json, updated_at, expires_at, deployment_id, session_id),
        )

        if cursor.rowcount == 0:
            raise KeyError(
                f"Session not found [session_id={session_id}] "
                f"[deployment_id={deployment_id}]"
            )

        logger.debug(
            f"Updated session [session_id={session_id}] "
            f"[deployment_id={deployment_id}]"
        )

        with self._lock, self._conn:
            row = self._conn.execute(
                """
                SELECT session_id, pipeline_id, state_json,
                       created_at, updated_at, expires_at
                  FROM sessions
                 WHERE deployment_id = ? AND session_id = ?
                """,
                (deployment_id, session_id),
            ).fetchone()

        if not row:
            raise KeyError(
                f"Session not found after update [session_id={session_id}] "
                f"[deployment_id={deployment_id}]"
            )

        return self._row_to_session(row, deployment_id)

    def delete(self, session_id: str, deployment_id: str) -> None:
        """Delete a session (silent if not found).

        Args:
            session_id: The session identifier.
            deployment_id: The deployment identifier.
        """
        cursor = self._execute_with_retry(
            """
            DELETE FROM sessions
             WHERE deployment_id = ? AND session_id = ?
            """,
            (deployment_id, session_id),
        )

        if cursor.rowcount > 0:
            logger.info(
                f"Deleted session [session_id={session_id}] "
                f"[deployment_id={deployment_id}]"
            )

    def cleanup(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed.
        """
        now = datetime.now(timezone.utc).isoformat()

        cursor = self._execute_with_retry(
            """
            DELETE FROM sessions
             WHERE expires_at IS NOT NULL AND expires_at <= ?
            """,
            (now,),
        )

        removed_count = cursor.rowcount
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired sessions")

        return removed_count

    def _execute_with_retry(
        self,
        sql: str,
        params: Tuple[Any, ...] = (),
    ) -> sqlite3.Cursor:
        """Execute SQL with retry logic for locked database.

        Args:
            sql: SQL statement to execute.
            params: Parameters for the SQL statement.

        Returns:
            The cursor from the execution.

        Raises:
            sqlite3.OperationalError: If database remains locked after retries.
            Exception: If any other exception occurs during execution.
            OperationalError: If database remains locked after retries.
        """
        delay = self.config.retry_base_delay

        for attempt in range(self.config.max_retry_attempts):
            try:
                with self._lock:
                    self._conn.execute("BEGIN IMMEDIATE")
                    try:
                        cursor = self._conn.execute(sql, params)
                        self._conn.commit()
                        return cursor
                    except Exception:
                        self._conn.rollback()
                        raise
            except sqlite3.OperationalError as e:
                if "database is locked" not in str(e).lower():
                    raise
                if attempt == self.config.max_retry_attempts - 1:
                    logger.error(
                        f"Database locked after {self.config.max_retry_attempts} attempts"
                    )
                    raise

                time.sleep(delay)
                delay *= 2

        raise sqlite3.OperationalError("Unexpected retry loop exit")

    def _row_to_session(self, row: sqlite3.Row, deployment_id: str) -> Session:
        """Convert a database row to a Session object.

        Args:
            row: SQLite row from sessions table.
            deployment_id: The deployment identifier.

        Returns:
            Session object constructed from the row.
        """
        state = json.loads(row["state_json"])

        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])
        expires_at = (
            datetime.fromisoformat(row["expires_at"])
            if row["expires_at"]
            else None
        )

        return Session(
            id=row["session_id"],
            deployment_id=deployment_id,
            pipeline_id=row["pipeline_id"],
            state=state,
            created_at=created_at,
            updated_at=updated_at,
            expires_at=expires_at,
        )
