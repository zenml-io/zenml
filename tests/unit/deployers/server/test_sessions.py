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
"""Unit tests for session infrastructure."""

import multiprocessing
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from zenml.deployers.server.sessions import (
    InMemorySessionBackend,
    LocalSessionBackend,
    SessionManager,
)


class TestInMemorySessionBackend:
    """Test InMemorySessionBackend storage and eviction."""

    def test_inmemory_backend_performs_lru_eviction(self):
        """Test that LRU eviction removes least-recently-used sessions."""
        backend = InMemorySessionBackend(max_sessions=1)
        deployment_id = "deployment-1"

        # Create first session
        s1 = backend.create(
            session_id="session-1",
            deployment_id=deployment_id,
            initial_state={"data": "first"},
        )
        assert s1.id == "session-1"

        # Verify first session is loadable
        loaded_s1 = backend.load("session-1", deployment_id)
        assert loaded_s1 is not None
        assert loaded_s1.id == "session-1"

        # Create second session (should evict first due to capacity=1)
        s2 = backend.create(
            session_id="session-2",
            deployment_id=deployment_id,
            initial_state={"data": "second"},
        )
        assert s2.id == "session-2"

        # First session should be evicted
        evicted_s1 = backend.load("session-1", deployment_id)
        assert evicted_s1 is None

        # Second session should still be present
        loaded_s2 = backend.load("session-2", deployment_id)
        assert loaded_s2 is not None
        assert loaded_s2.id == "session-2"

    def test_inmemory_backend_lazy_expiration_removes_stale_sessions(self):
        """Test that expired sessions are removed on load."""
        backend = InMemorySessionBackend()
        deployment_id = "deployment-1"
        session_id = "session-expired"

        # Create session with TTL
        session = backend.create(
            session_id=session_id,
            deployment_id=deployment_id,
            initial_state={"data": "value"},
            ttl_seconds=1,
        )
        assert session.expires_at is not None

        # Manually expire the session by setting expires_at to the past
        key = (deployment_id, session_id)
        stored_session = backend._sessions[key]
        stored_session.expires_at = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )

        # Attempt to load - should return None and remove the session
        loaded = backend.load(session_id, deployment_id)
        assert loaded is None

        # Verify session was removed from storage
        assert key not in backend._sessions


class TestSessionManager:
    """Test SessionManager orchestration logic."""

    def test_session_manager_resolves_existing_session(self):
        """Test that SessionManager can resolve existing sessions by ID."""
        backend = InMemorySessionBackend()
        manager = SessionManager(backend=backend, ttl_seconds=3600)
        deployment_id = "deployment-1"

        # Resolve without providing ID (should generate new session)
        session1 = manager.resolve(
            requested_id=None,
            deployment_id=deployment_id,
            pipeline_id="pipeline-1",
        )
        assert session1.id is not None
        assert session1.deployment_id == deployment_id

        # Resolve again with the same ID (should return existing session)
        session2 = manager.resolve(
            requested_id=session1.id,
            deployment_id=deployment_id,
            pipeline_id="pipeline-1",
        )
        assert session2.id == session1.id
        assert session2.deployment_id == session1.deployment_id

        # Verify it's the same session (state should be preserved)
        session1_updated = manager.persist_state(session1, {"counter": 42})
        session2_reloaded = manager.resolve(
            requested_id=session1.id,
            deployment_id=deployment_id,
        )
        assert (
            session2_reloaded.state["counter"]
            == session1_updated.state["counter"]
        )

    def test_session_manager_enforces_state_size_limit(self):
        """Test that SessionManager rejects oversized state payloads."""
        backend = InMemorySessionBackend()
        manager = SessionManager(
            backend=backend,
            ttl_seconds=3600,
            max_state_bytes=100,  # Very small limit for testing
        )
        deployment_id = "deployment-1"

        # Resolve a session
        session = manager.resolve(
            requested_id=None,
            deployment_id=deployment_id,
        )

        # Attempt to persist state that exceeds the limit
        large_state = {"data": "x" * 100000}  # Much larger than 10 bytes

        with pytest.raises(ValueError, match="exceeds maximum allowed"):
            manager.persist_state(session, large_state)

        # Verify small state works fine
        small_state = {"ok": "y"}  # Should be under 10 bytes
        updated = manager.persist_state(session, small_state)
        assert updated.state == small_state


class TestLocalSessionBackend:
    """Test LocalSessionBackend SQLite-based storage."""

    @pytest.fixture
    def temp_db_path(self):
        """Provide a temporary database path for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "sessions.db"

    def test_local_backend_crud_roundtrip(self, temp_db_path):
        """Test basic CRUD operations on local backend."""
        backend = LocalSessionBackend(db_path=temp_db_path)
        deployment_id = "deployment-1"
        session_id = "session-1"

        # Create session
        session = backend.create(
            session_id=session_id,
            deployment_id=deployment_id,
            pipeline_id="pipeline-1",
            initial_state={"counter": 0},
            ttl_seconds=3600,
        )
        assert session.id == session_id
        assert session.deployment_id == deployment_id
        assert session.pipeline_id == "pipeline-1"
        assert session.state == {"counter": 0}
        assert session.expires_at is not None

        # Load session
        loaded = backend.load(session_id, deployment_id)
        assert loaded is not None
        assert loaded.id == session_id
        assert loaded.state == {"counter": 0}

        # Update session
        updated = backend.update(
            session_id,
            deployment_id,
            {"counter": 42},
            ttl_seconds=7200,
        )
        assert updated.state == {"counter": 42}

        # Verify update persisted
        reloaded = backend.load(session_id, deployment_id)
        assert reloaded is not None
        assert reloaded.state == {"counter": 42}

        # Delete session
        backend.delete(session_id, deployment_id)
        deleted = backend.load(session_id, deployment_id)
        assert deleted is None

    def test_local_backend_duplicate_create_raises(self, temp_db_path):
        """Test that creating a duplicate session raises ValueError."""
        backend = LocalSessionBackend(db_path=temp_db_path)
        deployment_id = "deployment-1"
        session_id = "session-1"

        backend.create(
            session_id=session_id,
            deployment_id=deployment_id,
            initial_state={},
        )

        with pytest.raises(ValueError, match="already exists"):
            backend.create(
                session_id=session_id,
                deployment_id=deployment_id,
                initial_state={},
            )

    def test_local_backend_update_missing_raises(self, temp_db_path):
        """Test that updating a non-existent session raises KeyError."""
        backend = LocalSessionBackend(db_path=temp_db_path)

        with pytest.raises(KeyError, match="not found"):
            backend.update(
                session_id="nonexistent",
                deployment_id="deployment-1",
                state={},
            )

    def test_local_backend_delete_is_idempotent(self, temp_db_path):
        """Test that deleting a non-existent session is silent."""
        backend = LocalSessionBackend(db_path=temp_db_path)
        # Should not raise
        backend.delete("nonexistent", "deployment-1")

    def test_local_backend_lazy_expiration(self, temp_db_path):
        """Test that expired sessions are removed on load."""
        backend = LocalSessionBackend(db_path=temp_db_path)
        deployment_id = "deployment-1"
        session_id = "session-expired"

        # Create session with very short TTL
        backend.create(
            session_id=session_id,
            deployment_id=deployment_id,
            initial_state={"data": "value"},
            ttl_seconds=1,
        )

        # Manually set expiration to the past

        with backend._lock, backend._conn:
            past_time = (
                datetime.now(timezone.utc) - timedelta(seconds=10)
            ).isoformat()
            backend._conn.execute(
                "UPDATE sessions SET expires_at = ? WHERE session_id = ?",
                (past_time, session_id),
            )
            backend._conn.commit()

        # Load should detect expiration and delete
        loaded = backend.load(session_id, deployment_id)
        assert loaded is None

        # Verify session was deleted
        with backend._lock, backend._conn:
            row = backend._conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            assert row is None

    def test_local_backend_cleanup_removes_expired(self, temp_db_path):
        """Test that cleanup removes all expired sessions."""
        backend = LocalSessionBackend(db_path=temp_db_path)
        deployment_id = "deployment-1"

        # Create valid session
        backend.create(
            session_id="session-valid",
            deployment_id=deployment_id,
            initial_state={},
            ttl_seconds=3600,
        )

        # Create expired session
        backend.create(
            session_id="session-expired",
            deployment_id=deployment_id,
            initial_state={},
            ttl_seconds=1,
        )

        # Manually expire the second session

        with backend._lock, backend._conn:
            past_time = (
                datetime.now(timezone.utc) - timedelta(seconds=10)
            ).isoformat()
            backend._conn.execute(
                "UPDATE sessions SET expires_at = ? WHERE session_id = ?",
                (past_time, "session-expired"),
            )
            backend._conn.commit()

        # Run cleanup
        removed_count = backend.cleanup()
        assert removed_count == 1

        # Valid session should still exist
        valid = backend.load("session-valid", deployment_id)
        assert valid is not None

        # Expired session should be gone
        expired = backend.load("session-expired", deployment_id)
        assert expired is None

    def test_local_backend_deployment_isolation(self, temp_db_path):
        """Test that sessions are isolated by deployment_id."""
        backend = LocalSessionBackend(db_path=temp_db_path)

        # Create sessions in different deployments
        backend.create(
            session_id="session-1",
            deployment_id="deployment-A",
            initial_state={"deploy": "A"},
        )
        backend.create(
            session_id="session-1",
            deployment_id="deployment-B",
            initial_state={"deploy": "B"},
        )

        # Both should be loadable with correct data
        session_a = backend.load("session-1", "deployment-A")
        session_b = backend.load("session-1", "deployment-B")

        assert session_a is not None
        assert session_b is not None
        assert session_a.state == {"deploy": "A"}
        assert session_b.state == {"deploy": "B"}

    def test_local_backend_survives_reconnection(self, temp_db_path):
        """Test that sessions persist across backend instances."""
        deployment_id = "deployment-1"
        session_id = "session-persistent"

        # Create session with first backend instance
        backend1 = LocalSessionBackend(db_path=temp_db_path)
        backend1.create(
            session_id=session_id,
            deployment_id=deployment_id,
            initial_state={"value": 123},
        )
        del backend1

        # Load session with second backend instance
        backend2 = LocalSessionBackend(db_path=temp_db_path)
        loaded = backend2.load(session_id, deployment_id)
        assert loaded is not None
        assert loaded.state == {"value": 123}

    def test_local_backend_concurrent_writes(self, temp_db_path):
        """Test that concurrent writes are handled correctly."""
        backend = LocalSessionBackend(db_path=temp_db_path)
        deployment_id = "deployment-1"

        # Create multiple sessions rapidly
        import threading

        def create_session(session_id):
            try:
                backend.create(
                    session_id=session_id,
                    deployment_id=deployment_id,
                    initial_state={"id": session_id},
                )
            except Exception:
                pass  # Ignore errors for this test

        threads = []
        for i in range(10):
            t = threading.Thread(target=create_session, args=(f"session-{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify sessions were created
        for i in range(10):
            loaded = backend.load(f"session-{i}", deployment_id)
            assert loaded is not None


class TestLocalSessionBackendMultiprocess:
    """Test LocalSessionBackend multi-process scenarios."""

    @pytest.fixture
    def temp_db_path(self):
        """Provide a temporary database path for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "sessions.db"

    def test_multiprocess_shared_state(self, temp_db_path):
        """Test that multiple processes can share session state."""

        def process_writer(db_path, session_id, value):
            """Process that writes a session."""
            backend = LocalSessionBackend(db_path=db_path)
            backend.create(
                session_id=session_id,
                deployment_id="deployment-1",
                initial_state={"value": value},
            )

        def process_reader(db_path, session_id, expected_value):
            """Process that reads a session."""
            backend = LocalSessionBackend(db_path=db_path)
            session = backend.load(session_id, "deployment-1")
            assert session is not None
            assert session.state["value"] == expected_value

        # Process A writes
        p1 = multiprocessing.Process(
            target=process_writer, args=(temp_db_path, "session-1", 42)
        )
        p1.start()
        p1.join()
        assert p1.exitcode == 0

        # Process B reads
        p2 = multiprocessing.Process(
            target=process_reader, args=(temp_db_path, "session-1", 42)
        )
        p2.start()
        p2.join()
        assert p2.exitcode == 0


class TestSessionManagerWithLocalBackend:
    """Test SessionManager with LocalSessionBackend."""

    @pytest.fixture
    def temp_db_path(self):
        """Provide a temporary database path for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "sessions.db"

    def test_session_manager_with_local_backend(self, temp_db_path):
        """Test SessionManager works correctly with local backend."""
        backend = LocalSessionBackend(db_path=temp_db_path)
        manager = SessionManager(
            backend=backend, ttl_seconds=3600, max_state_bytes=1024
        )
        deployment_id = "deployment-1"

        # Resolve new session
        session = manager.resolve(
            requested_id=None,
            deployment_id=deployment_id,
            pipeline_id="pipeline-1",
        )
        assert session.id is not None

        # Persist state
        updated = manager.persist_state(session, {"counter": 1})
        assert updated.state == {"counter": 1}

        # Resolve existing session
        resolved = manager.resolve(
            requested_id=session.id,
            deployment_id=deployment_id,
        )
        assert resolved.id == session.id
        assert resolved.state == {"counter": 1}
