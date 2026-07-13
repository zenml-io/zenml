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
"""Tests for the server-side artifact store cache."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.zen_server.artifact_store_cache import ArtifactStoreCache


def _model(id_=None, updated=None, connector_updated=None):
    """Build a fake component model exposing id, updated, name and connector."""
    connector = (
        SimpleNamespace(updated=connector_updated)
        if connector_updated is not None
        else None
    )
    return SimpleNamespace(
        id=id_ or uuid4(),
        updated=updated or datetime(2024, 1, 1),
        name="artifact-store",
        connector=connector,
    )


@pytest.fixture
def built_stores():
    """Patch `from_model` to return a fresh mock store per call."""
    stores = []

    def _build(model):
        store = MagicMock(name=f"store-{len(stores)}")
        stores.append(store)
        return store

    with patch("zenml.stack.StackComponent.from_model", side_effect=_build):
        yield stores


def test_same_model_reuses_instance(built_stores):
    """The same model returns the same cached instance, built once."""
    cache = ArtifactStoreCache()
    model = _model()

    first = cache.get_or_create(model)
    second = cache.get_or_create(model)

    assert first is second
    assert len(built_stores) == 1


def test_updated_timestamp_rebuilds_without_cleanup(built_stores):
    """A changed `updated` timestamp rebuilds without cleaning up the old store.

    Cleanup is deferred to GC because a concurrent request may still hold the
    old instance.
    """
    cache = ArtifactStoreCache()
    component_id = uuid4()

    old = cache.get_or_create(_model(component_id, datetime(2024, 1, 1)))
    new = cache.get_or_create(_model(component_id, datetime(2024, 6, 1)))

    assert old is not new
    assert len(built_stores) == 2
    old.cleanup.assert_not_called()


def test_connector_update_rebuilds(built_stores):
    """A newer connector `updated` timestamp invalidates the cached store."""
    cache = ArtifactStoreCache()
    component_id = uuid4()

    old = cache.get_or_create(
        _model(
            component_id,
            updated=datetime(2024, 1, 1),
            connector_updated=datetime(2024, 1, 1),
        )
    )
    # Connector rotated after the component was last updated.
    new = cache.get_or_create(
        _model(
            component_id,
            updated=datetime(2024, 1, 1),
            connector_updated=datetime(2024, 6, 1),
        )
    )

    assert old is not new
    assert len(built_stores) == 2


def test_ttl_expiry_rebuilds_without_cleanup(built_stores):
    """An entry past its TTL is rebuilt without cleaning up the old store."""
    cache = ArtifactStoreCache(ttl=0.0)
    model = _model()

    first = cache.get_or_create(model)
    second = cache.get_or_create(model)

    assert first is not second
    first.cleanup.assert_not_called()


def test_lru_eviction_drops_oldest_without_cleanup(built_stores):
    """Exceeding the size cap evicts the oldest entry without cleaning it up."""
    cache = ArtifactStoreCache(max_size=2)

    a = cache.get_or_create(_model())
    b = cache.get_or_create(_model())
    c = cache.get_or_create(_model())

    # inserting the third entry evicts the least-recently-used (a)
    assert len(cache._entries) == 2
    a.cleanup.assert_not_called()
    b.cleanup.assert_not_called()
    c.cleanup.assert_not_called()


def test_clear_cleans_up_all(built_stores):
    """Clearing the cache cleans up every cached store."""
    cache = ArtifactStoreCache()
    a = cache.get_or_create(_model())
    b = cache.get_or_create(_model())

    cache.clear()

    a.cleanup.assert_called_once()
    b.cleanup.assert_called_once()
    assert len(cache._entries) == 0
