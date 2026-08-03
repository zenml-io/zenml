---
description: Collecting and exporting runtime resource metrics from your ML pipelines.
icon: gauge-high
---

# Metric Stores

The metric store is a stack component responsible for collecting runtime resource metrics — CPU, GPU, and memory utilization — while your pipeline steps execute, and exporting them to an observability backend.

### How it works

Metrics have no natural producer — nothing emits a "CPU is at 73%" event on its own — so the metric store samples the system itself:

1. **Per-step sampling context**: When a step starts, ZenML wraps it in a metric sampling context that is active for the duration of the step.

2. **Background sampler thread**: That context starts a small background thread which, every few seconds, reads CPU / memory via [`psutil`](https://pypi.org/project/psutil/) (and optionally GPU via `pynvml`) and pushes one measurement into the active metric store.

3. **Off-thread export**: The store hands measurements to an OpenTelemetry meter; a batch reader exports them to your backend on its *own* thread, so the network round-trip never blocks step execution.

Every sample carries identity labels (run id, step id, pipeline name, ...), so metrics for a given step line up alongside other ZenML telemetry in your dashboards.

### When to use it

The metric store is **opt-in and has no default**. A stack without one simply collects no metrics — nothing breaks. Configure one when:

- You want CPU / GPU / memory utilization for every step, visualized in Grafana, Prometheus, or any OpenTelemetry-compatible backend
- You are right-sizing infrastructure (e.g. spotting steps that under- or over-use a GPU)
- You want resource metrics correlated with your existing pipeline logs
- You are running at scale and need resource observability as a first-class signal

{% hint style="info" %}
A stack can have **at most one** metric store. Metrics are exported straight to your backend and are **never stored in ZenML's database** — there is no metrics table.
{% endhint %}

### How to use it

Register a metric store and attach it to your stack:

```shell
# Register an OpenTelemetry metric store
zenml metric-store register <METRIC_STORE_NAME> \
    --flavor=otel \
    --endpoint=https://otel-collector.example.com/v1/metrics

# Attach it to a stack (-M / --metric_store)
zenml stack register <STACK_NAME> \
    -a <ARTIFACT_STORE> \
    -o <ORCHESTRATOR> \
    -M <METRIC_STORE_NAME> \
    --set

# ...or add it to an existing stack
zenml stack update <STACK_NAME> -M <METRIC_STORE_NAME>
```

Once attached, resource metrics are collected automatically for every step of every run on that stack.

#### Optional GPU metrics

GPU sampling needs the optional [`pynvml`](https://pypi.org/project/pynvml/) dependency, which is kept out of the base package to stay lightweight:

```shell
pip install "pynvml>=11.5.0"
```

If `enable_gpu` is left on but `pynvml` (or a GPU) is unavailable, GPU metrics are simply skipped with a one-time warning — never an error.

### Viewing metrics

Metrics are viewed **in your observability backend** (Grafana, Prometheus, etc.), not in the ZenML dashboard. Because exporting is fire-and-forget, the metric store does not fetch metrics back into ZenML — the backend owns the data. A future backend-specific flavor could implement retrieval; see [Develop a Custom Metric Store](custom.md).

The metrics emitted per step are:

| Metric                          | Unit    | Source   |
|---------------------------------|---------|----------|
| `zenml.step.cpu_percent`        | percent | psutil   |
| `zenml.step.memory_percent`     | percent | psutil   |
| `zenml.step.memory_used_bytes`  | bytes   | psutil   |
| `zenml.step.process_memory_bytes` | bytes | psutil   |
| `zenml.step.gpu_utilization_percent` | percent | pynvml (optional) |
| `zenml.step.gpu_memory_used_bytes`   | bytes   | pynvml (optional) |

### Metric Store Flavors

| Metric Store                          | Flavor  | Integration | Notes                                                                                  |
|---------------------------------------|---------|-------------|----------------------------------------------------------------------------------------|
| [OtelMetricStore](otel.md)            | `otel`  | _built-in_  | Generic OpenTelemetry metric store for any OTLP-compatible backend. Export only.        |
| [Custom Implementation](custom.md)    | _custom_|             | Extend the metric store abstraction and provide your own implementation.                |

List the available flavors with:

```shell
zenml metric-store flavor list
```

{% hint style="info" %}
If you're interested in the base abstraction and how metric stores work internally, see [Develop a Custom Metric Store](custom.md).
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
