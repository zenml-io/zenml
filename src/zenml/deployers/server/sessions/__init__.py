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
"""Session backend implementations.

This package contains concrete implementations of the SessionBackend interface:
- InMemorySessionBackend: Thread-safe in-memory implementation with LRU eviction
- LocalSessionBackend: SQLite-backed implementation for multi-worker single-host deployments
- SessionManager: High-level orchestrator for session lifecycle management

The core abstractions (Session, SessionBackend) are defined in the parent
sessions.py module.
"""
from zenml.deployers.server.sessions.inmemory_session_backend import (
    InMemoryBackendConfig,
    InMemorySessionBackend,
)
from zenml.deployers.server.sessions.local_session_backend import (
    LocalBackendConfig,
    LocalSessionBackend,
)
from zenml.deployers.server.sessions.session_manager import SessionManager

__all__ = [
    "InMemoryBackendConfig",
    "LocalBackendConfig",
    "InMemorySessionBackend",
    "LocalSessionBackend",
    "SessionManager",
]

