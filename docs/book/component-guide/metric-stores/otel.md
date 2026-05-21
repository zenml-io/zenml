---
description: Exporting runtime resource metrics to any OpenTelemetry-compatible backend.
---

# OpenTelemetry Metric Store

The OpenTelemetry (OTEL) Metric Store is a metric store flavor that exports per-step CPU / GPU / memory utilization to any OpenTelemetry-compatible backend using the OTLP/HTTP protocol with JSON encoding. Built on the [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/), it slots into an existing Prometheus / Grafana / OTEL Collector setup with no extra infrastructure.

{% hint style="warning" %}
The OTEL Metric Store is **export-only**. It ships metrics to an OTLP endpoint but cannot fetch them back into the ZenML dashboard — the backend (e.g. Prometheus) owns the data, so you query it there. If you need retrieval, you can extend this store and implement `fetch()` for your backend. See [Develop a Custom Metric Store](custom.md).
{% endhint %}

### When to use it

The OTEL Metric Store is ideal when:

- You already run an OpenTelemetry-compatible stack (OTEL Collector, Grafana, Prometheus, Honeycomb, Dash0, ...)
- You want CPU / GPU / memory utilization per step, correlated with your pipeline logs by the same identity labels
- You need to right-size compute (spot GPU under-utilization, memory pressure, ...)
- You want resource observability without adding a database or new infrastructure

### How it works

1. **Sampling**: A per-step background thread reads CPU / memory via `psutil` (and GPU via the optional `pynvml`) every `sampling_interval_seconds`.

2. **OTEL conversion**: Each measurement is written to a synchronous OpenTelemetry `Gauge` (one per metric name, e.g. `zenml.step.cpu_percent`), tagged with ZenML identity attributes.

3. **Batching**: A `PeriodicExportingMetricReader` drains the gauges on its own thread every `export_interval_seconds` — step execution is never blocked on the network.

4. **Export**: Batched metrics are sent to your endpoint using OTLP/HTTP with JSON encoding.

#### ZenML-specific attributes

Every sample carries the same identity labels as logs, so the two line up in your dashboards:

| Attribute                  | Description                                            |
|----------------------------|--------------------------------------------------------|
| `zenml.pipeline.id`        | Pipeline ID                                            |
| `zenml.pipeline.name`      | Pipeline name                                          |
| `zenml.pipeline.run.id`    | Pipeline run ID                                        |
| `zenml.pipeline.run.name`  | Pipeline run name                                      |
| `zenml.step.run.id`        | Step run ID                                            |
| `zenml.step.run.name`      | Step run name                                          |
| `zenml.stack.id`           | Stack ID                                               |
| `zenml.stack.name`         | Stack name                                             |
| `zenml.project.id`         | Project ID                                             |
| `zenml.project.name`       | Project name                                           |
| `zenml.user.id`            | User ID                                                |
| `zenml.user.name`          | User name                                              |
| `zenml.workspace.id`       | Workspace ID (when connected to a ZenML Pro workspace) |
| `zenml.workspace.name`     | Workspace name (when connected to a ZenML Pro workspace) |

### How to use it

You need an OpenTelemetry-compatible endpoint that accepts OTLP/HTTP with JSON encoding (a self-hosted OTEL Collector, Grafana Cloud, etc.):

```shell
# Register an OTEL metric store
zenml metric-store register my_otel_metrics \
    --flavor=otel \
    --endpoint=https://otel-collector.example.com/v1/metrics

# Attach it to a stack
zenml stack register my_stack \
    -a my_artifact_store \
    -o default \
    -M my_otel_metrics \
    --set
```

#### With authentication headers

Most managed backends require authentication. Pass headers using a ZenML secret so credentials are never stored in plain text:

```shell
zenml secret create otel_auth --api_key=<YOUR_API_KEY>

zenml metric-store register my_otel_metrics \
    --flavor=otel \
    --endpoint=https://otel-collector.example.com/v1/metrics \
    --headers='{"Authorization": "Bearer {{otel_auth.api_key}}"}'
```

#### Enabling GPU metrics

GPU sampling needs the optional `pynvml` dependency (kept out of the base package to stay lightweight):

```shell
pip install "zenml[gpu-metrics]"
```

`enable_gpu` defaults to `True`; if `pynvml` or a GPU is unavailable, GPU metrics are skipped with a one-time warning rather than an error.

### Configuration options

| Parameter                   | Default        | Description                                                              |
|-----------------------------|----------------|--------------------------------------------------------------------------|
| `endpoint`                  | _required_     | OTLP/HTTP endpoint URL for metric ingestion                              |
| `sampling_interval_seconds` | `10.0`         | Seconds between system utilization samples                               |
| `enable_gpu`                | `True`         | Whether to sample GPU utilization via optional `pynvml`                  |
| `export_interval_seconds`   | `30.0`         | Seconds between batch exports to the collector (off the step thread)     |
| `export_timeout_seconds`    | `10.0`         | Network timeout for a single OTLP export request                         |
| `headers`                   | `None`         | Optional headers for authentication                                      |
| `service_name`              | `"zenml"`      | Service name in OTEL resource attributes                                 |
| `service_version`           | ZenML version  | Service version in OTEL resource attributes                              |

### Retry behavior

The exporter includes built-in retry logic for transient failures:

- **Retried status codes**: 408, 429, 500, 502, 503, 504
- **Connection / read retries**: 5 attempts with exponential backoff
- **Backoff factor**: 0.5 seconds

This keeps a flaky collector from dropping a step's metrics.

### Limitations

1. **No metric fetching**: Metrics cannot be retrieved into the ZenML dashboard; view them in your observability backend.

2. **Endpoint compatibility**: Your endpoint must accept OTLP/HTTP with JSON encoding.

3. **One per stack**: A stack can have at most one metric store.

### Best practices

1. **Mind label cardinality**: Every sample is tagged with `zenml.pipeline.run.id` and `zenml.step.run.id`. These are high-cardinality labels — pipelines with thousands of steps create many time series in Prometheus. Tune `sampling_interval_seconds` upward (e.g. `30.0`) for long, step-heavy pipelines, and consider recording rules / retention policies on the backend.

2. **Tune the sampling vs. export trade-off**: Lower `sampling_interval_seconds` gives finer resolution at higher overhead; raise `export_interval_seconds` to reduce export traffic for low-volume pipelines.

3. **Use secrets for credentials**: Always store API keys / tokens in ZenML secrets, never in plain text.

4. **Install the GPU extra only where needed**: Keep `zenml[gpu-metrics]` on GPU worker images; CPU-only clients don't need it.

For the full list of configurable attributes, see the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-metric_stores.html#zenml.metric_stores.otel.otel_metric_store).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
