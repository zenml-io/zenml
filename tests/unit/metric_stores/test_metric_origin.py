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
"""Unit tests for the stable per-origin id and its export on samples.

The origin id is the primary handle a future fetch-capable metric store
keys on, so it must be unique per stream and ride on every exported
sample independent of the (shared) ZenML identity metadata.
"""

import uuid
from datetime import datetime
from unittest import mock

from zenml.metric_stores.base_metric_store import (
    METRIC_ORIGIN_ID_ATTRIBUTE,
    BaseMetricStore,
)


def _build_store() -> BaseMetricStore:
    """Build an OTel metric store instance without activating it.

    Returns:
        An un-activated ``OtelMetricStore`` (no OTel pipeline / threads
        are created until an origin is registered).
    """
    from zenml.metric_stores.otel.otel_flavor import OtelMetricStoreFlavor

    flavor = OtelMetricStoreFlavor()
    config = flavor.config_class(endpoint="http://collector:4318/v1/metrics")
    return flavor.implementation_class(
        name="t",
        id=uuid.uuid4(),
        config=config,
        flavor="otel",
        type=flavor.type,
        user=uuid.uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_origins_get_distinct_stable_ids() -> None:
    """Two origins receive different ids, each stable across reads."""
    store = _build_store()

    origin_a = store.origin_class("step-a", store, {})
    origin_b = store.origin_class("step-b", store, {})

    assert origin_a.id and origin_b.id
    assert origin_a.id != origin_b.id
    # Minted once: the same value on repeated access (not regenerated).
    assert origin_a.id == origin_a.id


def test_record_stamps_origin_id_on_sample_attributes() -> None:
    """record() exports the origin id alongside identity + tick metadata."""
    store = _build_store()
    origin = store.origin_class("step-a", store, {"zenml.step.run.id": "S"})

    gauge = mock.Mock()
    with mock.patch.object(store, "_get_gauge", return_value=gauge):
        store.record(
            origin=origin,
            measurements={"cpu_percent": 50.0},
            metadata={"tick": "1"},
        )

    attributes = gauge.set.call_args.kwargs["attributes"]
    assert attributes[METRIC_ORIGIN_ID_ATTRIBUTE] == origin.id
    assert attributes["zenml.step.run.id"] == "S"
    assert attributes["tick"] == "1"


def test_per_tick_metadata_overrides_identity_metadata() -> None:
    """Per-tick metadata wins over identity metadata on key collisions."""
    store = _build_store()
    origin = store.origin_class("step-a", store, {"shared": "identity"})

    attributes = store._build_sample_attributes(
        origin, metadata={"shared": "tick"}
    )

    assert attributes["shared"] == "tick"
    assert attributes[METRIC_ORIGIN_ID_ATTRIBUTE] == origin.id
