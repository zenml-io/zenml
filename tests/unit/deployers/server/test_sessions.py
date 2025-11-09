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

from datetime import datetime, timedelta, timezone

import pytest

from zenml.deployers.server.sessions import (
    InMemorySessionBackend,
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
