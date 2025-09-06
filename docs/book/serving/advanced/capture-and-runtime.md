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

- OffStepRuntime
  - Focus: Lightweight operation with minimal overhead.
  - Behavior: Persists artifacts; skips metadata/logs/visualizations/caching (compiler disables these by default in OFF).

- MemoryStepRuntime
  - Focus: Pure in-memory execution (no server, no persistence).
  - Behavior: Inter-step data is exchanged via in-process memory handles; no runs or artifacts.
  - Configure with REALTIME: `capture={"mode": "REALTIME", "runs": "off"}` or `{"persistence": "memory"}`.

## Capture Configuration

Where to set:
- In code: `@pipeline(capture=...)`
- In run config YAML: `capture: ...`

Supported options (commonly used):
```yaml
capture:
  mode: BATCH | REALTIME | OFF | CUSTOM
  runs: on | off              # off → no runs (memory-only when REALTIME)
  persistence: sync | async | memory | off
  logs: all | errors-only | off
  metadata: true | false
  visualization: true | false
  cache_enabled: true | false
  code: true | false          # skip docstring/source capture if false
  flush_on_step_end: true | false
  ttl_seconds: 600            # Realtime cache TTL
  max_entries: 2048           # Realtime cache size bound
```

Notes:
- `mode` determines the base runtime.
- `runs: off` or `persistence: memory/off` under REALTIME maps to MemoryStepRuntime (pure in-memory execution).
- `flush_on_step_end`: If `false`, serving returns immediately; tracking is published asynchronously by the runtime worker.
- `code: false`: Skips docstring/source capture (metadata), but does not affect code execution.

## Serving Defaults

- REALTIME + serving context:
  - If `flush_on_step_end` is not provided, it defaults to `false` for better latency.
  - Users can override by setting `flush_on_step_end: true`.

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
  - `@pipeline(capture={"mode": "REALTIME", "flush_on_step_end": false})`

- Strict serving (strong consistency):
  - `@pipeline(capture={"mode": "REALTIME", "flush_on_step_end": true})`

- Memory-only (stateless service):
  - `@pipeline(capture={"mode": "REALTIME", "runs": "off"})`

- Compliance mode:
  - `@pipeline(capture="BATCH")` or
  - `@pipeline(capture={"mode": "REALTIME", "logs": "all", "metadata": true, "flush_on_step_end": true})`

## FAQ

- Can I enable only partial capture (e.g., errors-only logs)?
  - Yes, e.g., `logs: errors-only` and `metadata: false`.

- Does `code: false` break step execution?
  - No. It only disables docstring/source capture. Steps still run normally.

- How does caching interact with REALTIME?
  - Default caching behavior is unchanged. Set `cache_enabled: false` to bypass caching entirely.

- Can memory-only work with parallelism?
  - Memory-only is per-process. For multi-process/multi-container setups, use persistence for cross-process data.

