---
title: Capture Policy & Execution Runtimes (Advanced)
---

# Capture Policy & Execution Runtimes (Advanced)

This page explains how capture options map to execution runtimes and how to tune them for production serving.

## Execution Runtimes

- DefaultStepRuntime
  - Standard ZenML execution: persists artifacts, creates runs and step runs, captures metadata/logs per config.

- RealtimeStepRuntime
  - Focus: Low latency + observability.
  - Features:
    - In-process artifact value cache for downstream steps in the same process.
      - Tunables: `ttl_seconds`, `max_entries` via capture options (or env vars `ZENML_RT_CACHE_TTL_SECONDS`, `ZENML_RT_CACHE_MAX_ENTRIES`).
    - Async server updates with a background worker.
      - `flush_on_step_end` controls whether to block at step boundary to flush updates.
      - In serving with `mode=REALTIME`, `flush_on_step_end` defaults to `false` unless explicitly set.

- MemoryStepRuntime
  - Focus: Pure in-memory execution (no server, no persistence).
  - Behavior: Inter-step data is exchanged via in-process memory handles; no runs or artifacts.
  - Configure with REALTIME: `@pipeline(capture=Capture(memory_only=True))`.

## Capture Configuration

Where to set:
- In code: `@pipeline(capture=...)` (typed only)
- In run config YAML: `capture: REALTIME|BATCH`

Recommended API (typed)
```python
from zenml.capture.config import Capture

# Not required for defaults, but explicit usage examples:

# Realtime (default in serving), non-blocking reporting
@pipeline(capture=Capture())
def serve(...):
    ...

# Realtime, blocking reporting
@pipeline(capture=Capture(flush_on_step_end=True))

# Realtime, memory-only (serving only)
@pipeline(capture=Capture(memory_only=True))
```

Notes:
- Modes are inferred by context (batch vs serving), you only set options:
  - `flush_on_step_end`: If `False`, serving returns immediately; tracking is published asynchronously by the runtime worker.
  - `memory_only=True`: Pure in-memory execution (no runs/artifacts), serving only.
  - `code=False`: Skips docstring/source capture (metadata), but does not affect code execution.

## Serving Defaults

- REALTIME + serving context:
  - If capture is unset, defaults to non-blocking (`flush_on_step_end=False`).
  - Users can set `flush_on_step_end=True` to block at step boundary.

## Validation & Behavior

- Realtime capture outside serving:
  - Allowed for development; logs a warning and continues. In production, use the serving service.
- memory_only outside serving:
  - Ignored with a warning; standard execution proceeds (Batch/Realtime as applicable).
- Contradictory options:
  - Capture(memory_only=True, flush_on_step_end=True) → raises ValueError.

## Step Operators & Remote Execution

- Step operators inherit capture via environment (e.g., `ZENML_CAPTURE_MODE`).
- Remote entrypoints construct the matching runtime and honor capture options.

## Memory-Only Internals (for deeper understanding)

- Handle format: `mem://<run_id>/<upstream_step>/<output_name>`
- Memory runtime:
  - `resolve_step_inputs`: constructs handles from `run_id` + substitutions.
  - `load_input_artifact`: resolves handle to value from a thread-safe in-process store.
  - `store_output_artifacts`: stores outputs back to the store; returns new handles for downstream steps.
- No server calls; no runs or artifacts are created.

## Environment Variables

- `ZENML_CAPTURE_MODE`: global default capture when not set in the pipeline.
- `ZENML_SERVING_CAPTURE_DEFAULT`: used internally to reduce tracking when capture is not set (serving compatibility).
- `ZENML_RT_CACHE_TTL_SECONDS`, `ZENML_RT_CACHE_MAX_ENTRIES`: Realtime cache controls.

## Recipes

- Low-latency serving (eventual consistency):
  - `@pipeline(capture=Capture())`

- Strict serving (strong consistency):
  - `@pipeline(capture=Capture(flush_on_step_end=True))`

- Memory-only (stateless service):
  - `@pipeline(capture=Capture(memory_only=True))`

### Control logs/metadata/visualizations (Batch & Realtime)

These are pipeline settings, not capture options. Set them via `pipeline.configure(...)` or YAML:

```python
@pipeline()
def train(...):
    ...

# In code
train = train.with_options()
train.configure(
    enable_step_logs=True,
    enable_artifact_metadata=True,
    enable_artifact_visualization=False,
)
```

Or in run config YAML:

```yaml
enable_step_logs: true
enable_artifact_metadata: true
enable_artifact_visualization: false
```

### Disable code capture (docstring/source)

Code capture affects metadata only (not execution). You can disable it via capture in both modes:

```python
from zenml.capture.config import Capture

@pipeline(capture=Capture(code=False))
def serve(...):
    ...

@pipeline(capture=Capture(code=False))
def train(...):
    ...
```

## FAQ

- Can I enable only partial capture (e.g., errors-only logs)?
  - Yes, e.g., `logs: errors-only` and `metadata: false`.

- Does `code: false` break step execution?
  - No. It only disables docstring/source capture. Steps still run normally.

- How does caching interact with REALTIME?
  - Default caching behavior is unchanged. Set `cache_enabled: false` to bypass caching entirely.

- Can memory-only work with parallelism?
  - Memory-only is per-process. For multi-process/multi-container setups, use persistence for cross-process data.
