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
"""Unit tests for the Phase C metric read path (models + fetch contract)."""

import uuid
from datetime import datetime

import pytest

from zenml.models import MetricSample, MetricsResponse


def test_metric_sample_and_response_shape() -> None:
    """The plain read-path models build and default correctly."""
    sample = MetricSample(
        name="zenml.step.cpu_percent",
        value=73.4,
        timestamp=datetime.now(),
        attributes={"zenml.step.run.id": "abc"},
    )
    response = MetricsResponse(samples=[sample])

    assert response.samples[0].value == 73.4
    assert response.samples[0].attributes["zenml.step.run.id"] == "abc"
    # Envelope defaults: empty samples list, not truncated.
    assert MetricsResponse().samples == []
    assert MetricsResponse().truncated is False


def test_otel_metric_store_fetch_not_implemented() -> None:
    """OTel fetch raises NotImplementedError under the new signature."""
    from zenml.metric_stores.otel.otel_flavor import OtelMetricStoreFlavor

    flavor = OtelMetricStoreFlavor()
    config = flavor.config_class(endpoint="http://collector:4318/v1/metrics")
    store = flavor.implementation_class(
        name="t",
        id=uuid.uuid4(),
        config=config,
        flavor="otel",
        type=flavor.type,
        user=uuid.uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    with pytest.raises(NotImplementedError):
        store.fetch(filters={"run_id": "x"}, limit=10)


def test_fetch_metrics_rejects_client_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fetch_metrics must only run server-side (mirrors fetch_logs)."""
    from zenml.utils.metric_sampling_utils import fetch_metrics

    monkeypatch.delenv("ZENML_SERVER", raising=False)

    with pytest.raises(RuntimeError, match="server environment"):
        fetch_metrics(
            metric_store_id=uuid.uuid4(),
            zen_store=None,  # type: ignore[arg-type]
            filters={},
            limit=10,
        )
