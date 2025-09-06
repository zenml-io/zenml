---
title: Pipeline Serving Overview
---

# Pipeline Serving Overview

## What Is Pipeline Serving?

- Purpose: Expose a ZenML pipeline as a low-latency service (e.g., via FastAPI) that executes steps on incoming requests and returns results.
- Value: Production-grade orchestration with flexible capture policies to balance latency, observability, and lineage.
- Modes: Default batch-style execution, optimized realtime execution, and pure in-memory execution for maximum speed.

## Quick Start

1) Define your pipeline
- Use your normal `@pipeline` and `@step` definitions.
- No serving-specific changes required.

2) Choose a capture configuration (recommended)
- Low-latency, non-blocking tracking (serving-friendly):
  - `@pipeline(capture={"mode": "REALTIME", "flush_on_step_end": false})`
- Pure in-memory execution (no runs, no artifacts):
  - `@pipeline(capture={"mode": "REALTIME", "runs": "off"})`

3) Deploy the serving service with your preferred deployer and call the FastAPI endpoint.

## Capture Modes (Essentials)

- BATCH (default)
  - Behavior: Standard ZenML behavior (pipeline runs + step runs + artifacts + metadata/logs depending on config).
  - Use when: Full lineage and strong consistency are required.

- REALTIME
  - Behavior: Optimized for latency and throughput.
    - In-memory cache of artifact values within the same process.
    - Async server updates by default; in serving, defaults to non-blocking responses (tracking finishes in background).
  - Use when: You need low-latency serving with observability.

- OFF
  - Behavior: Lightweight tracking.
    - Persists artifacts but skips metadata/logs/visualizations/caching for reduced overhead.
  - Use when: You need a smaller footprint while preserving artifacts for downstream consumers.

- Memory-only (special case inside REALTIME)
  - Configure: `capture={"mode": "REALTIME", "runs": "off"}` or `capture={"mode": "REALTIME", "persistence": "memory"}`
  - Behavior: Pure in-memory execution:
    - No pipeline runs or step runs, no artifacts, no server calls.
    - Steps exchange data in-process; response returns immediately.
  - Use when: Maximum speed (prototyping, ultra-low-latency paths) without lineage.

## Where To Configure Capture

- In code (recommended)
  - `@pipeline(capture="REALTIME")`
  - `@pipeline(capture={"mode": "REALTIME", "flush_on_step_end": false})`

- In run config YAML
```yaml
capture: REALTIME

# or

capture:
  mode: REALTIME
  flush_on_step_end: false
```

- Environment (fallbacks)
  - `ZENML_CAPTURE_MODE=BATCH|REALTIME|OFF|CUSTOM`
  - Serving defaults leverage `ZENML_SERVING_CAPTURE_DEFAULT` when capture is not set (used internally to reduce tracking overhead).

## Best Practices

- Most users (serving-ready)
  - `capture={"mode": "REALTIME", "flush_on_step_end": false}`
  - Good balance of immediate response and production tracking.

- Maximum speed (no tracking at all)
  - `capture={"mode": "REALTIME", "runs": "off"}` (pure in-memory)
  - Great for tests, benchmarks, or hot paths where lineage is not needed.

- Compliance or rich lineage
  - `capture="BATCH"` or fine-tune REALTIME with `flush_on_step_end: true`, `logs: "all"`, `metadata: true`.

## FAQ (Essentials)

- Does serving always create pipeline runs?
  - BATCH/REALTIME/OFF: Yes (OFF reduces overhead of metadata/logs).
  - Memory-only (REALTIME with `runs: off`): No; executes purely in memory.

- Will serving block responses to flush tracking?
  - REALTIME in serving defaults to non-blocking (returns immediately), unless you explicitly set `flush_on_step_end: true`.

- Is memory-only safe for production?
  - Yes for stateless, speed-critical paths. Note: No lineage or persisted artifacts.

