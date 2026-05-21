---
description: Learning how to develop a custom metric store.
---

# Develop a Custom Metric Store

{% hint style="info" %}
Before diving into the specifics of this component type, it is beneficial to familiarize yourself with our [general guide to writing custom component flavors in ZenML](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component). This guide provides an essential understanding of ZenML's component flavor concepts.
{% endhint %}

ZenML ships an [OpenTelemetry Metric Store](./#metric-store-flavors) that exports to any OTLP-compatible backend. If you need a different backend — or you want to *retrieve* metrics back into ZenML — you can extend ZenML with your own metric store implementation.

### Base Abstraction

The metric store collects runtime resource metrics during step execution and exports them. The key thing to understand is that, unlike logs, **metrics have no external producer** — the sampler in `zenml.utils.metric_sampling_utils` generates measurements on a timer and pushes them in via `record()`. The origin lifecycle, flush semantics, and the read path mirror the [Log Store](../log-stores/custom.md) on purpose.

1. **Origins**: A `BaseMetricStoreOrigin` represents the source of measurements (a step execution) and carries the identity labels (run id, step id, ...) stamped on every sample. You `register_origin()` when a step starts and `deregister_origin()` when it ends — deregistering the last origin triggers a `flush()`.

2. **Core methods**: four abstract methods must be implemented:
   - `record()` — write one set of measurements for an origin (the metric analogue of the log store's `emit()`; called by the sampler, not an external stream)
   - `_release_origin()` — called when an origin is done (release resources)
   - `flush()` — ensure pending samples are exported
   - `fetch()` — retrieve samples for display (return a `MetricsResponse`)

3. **No database**: metrics are never persisted in ZenML's database, so `fetch()` takes plain identity `filters` (a dict) rather than a DB-backed model, and `MetricsResponse` is a plain `BaseModel`.

4. **Thread safety**: the base class manages the origin registry under a lock; inherit that behavior and only implement the four methods above.

Here's a simplified view of the base implementation:

```python
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from zenml.enums import StackComponentType
from zenml.models import MetricsResponse
from zenml.stack import Flavor, StackComponent, StackComponentConfig


class BaseMetricStoreConfig(StackComponentConfig):
    """Flavor-agnostic sampler knobs live here."""

    sampling_interval_seconds: float = 10.0
    enable_gpu: bool = True


class BaseMetricStore(StackComponent, ABC):
    # register_origin / deregister_origin are concrete on the base.

    @abstractmethod
    def record(
        self,
        origin: "BaseMetricStoreOrigin",
        measurements: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None: ...

    @abstractmethod
    def _release_origin(self, origin: "BaseMetricStoreOrigin") -> None: ...

    @abstractmethod
    def flush(self, blocking: bool = True) -> None: ...

    @abstractmethod
    def fetch(
        self,
        filters: Dict[str, Any],
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> MetricsResponse: ...


class BaseMetricStoreFlavor(Flavor):
    @property
    def type(self) -> StackComponentType:
        return StackComponentType.METRIC_STORE
```

### Building your own Metric Store

To create a custom metric store flavor:

1. **Implement the store**: Subclass `BaseMetricStore` and implement the four abstract methods. For an export-only backend, `fetch()` may simply `raise NotImplementedError` (as the built-in OTEL store does). To support dashboard retrieval, implement `fetch()` to query your backend and return a `MetricsResponse` of `MetricSample`s.

2. **Define the config**: Subclass `BaseMetricStoreConfig` with backend-specific options (endpoint, headers, ...). Keep sampler-related knobs on the base config.

3. **Register the flavor**: Subclass `BaseMetricStoreFlavor`, returning your config and implementation classes.

```python
from zenml.metric_stores.base_metric_store import (
    BaseMetricStore,
    BaseMetricStoreConfig,
    BaseMetricStoreFlavor,
)


class MyMetricStoreConfig(BaseMetricStoreConfig):
    endpoint: str


class MyMetricStore(BaseMetricStore):
    def record(self, origin, measurements, metadata=None): ...
    def _release_origin(self, origin): ...
    def flush(self, blocking=True): ...
    def fetch(self, filters, limit, start_time=None, end_time=None):
        raise NotImplementedError("Query the backend directly.")


class MyMetricStoreFlavor(BaseMetricStoreFlavor):
    @property
    def name(self) -> str:
        return "my_metric_store"

    @property
    def config_class(self):
        return MyMetricStoreConfig

    @property
    def implementation_class(self):
        return MyMetricStore
```

Then register it:

```shell
zenml metric-store flavor register <path.to.MyMetricStoreFlavor>
```

{% hint style="info" %}
The sampler (`zenml.utils.metric_sampling_utils.MetricSamplingContext`) is flavor-agnostic — any metric store you implement automatically gets per-step CPU / memory / GPU sampling. You only need to handle `record()` / export.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
