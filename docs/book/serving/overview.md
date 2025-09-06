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

2) Choose capture only when you need to change defaults
- You don’t need to set capture in most cases:
  - Normal runs default to Batch.
  - Serving defaults to Realtime (non-blocking).
- Optional tweaks (typed API only):
  - Low-latency, non-blocking (explicit): `@pipeline(capture=Capture())`
  - Blocking realtime (serving): `@pipeline(capture=Capture(flush_on_step_end=True))`
  - Pure in-memory (serving only): `@pipeline(capture=Capture(memory_only=True))`

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

- Memory-only (special case inside REALTIME)
  - Behavior: Pure in-memory execution:
    - No pipeline runs or step runs, no artifacts, no server calls.
    - Steps exchange data in-process; response returns immediately.
  - Use when: Maximum speed (prototyping, ultra-low-latency paths) without lineage.
  - Note: Outside serving contexts, `memory_only=True` is ignored with a warning and standard execution proceeds.

## Where To Configure Capture

- In code (typed only)
  - `@pipeline(capture=Capture())`
  - `@pipeline(capture=Capture(flush_on_step_end=False))`

- In run config YAML
```yaml
capture: REALTIME  # or BATCH
```

- Environment (fallbacks)
  - `ZENML_CAPTURE_MODE=BATCH|REALTIME`
  - Serving sets `ZENML_SERVING_CAPTURE_DEFAULT` internally to switch default to Realtime when capture is not set.

## Best Practices

- Most users (serving-ready)
  - `@pipeline(capture=Capture())`
  - Good balance of immediate response and production tracking.

- Maximum speed (no tracking at all)
  - `@pipeline(capture=Capture(memory_only=True))`
  - Great for tests, benchmarks, or hot paths where lineage is not needed.

- Compliance or rich lineage
  - Use Batch (default in non-serving) or set: `@pipeline(capture=Capture(flush_on_step_end=True))`.

## FAQ (Essentials)

- Does serving always create pipeline runs?
  - Batch/Realtime: Yes.
  - Memory-only (Realtime with `memory_only=True`): No; executes purely in memory.

- Will serving block responses to flush tracking?
  - Realtime in serving defaults to non-blocking (returns immediately), unless you set `flush_on_step_end=True`.

- Is memory-only safe for production?
  - Yes for stateless, speed-critical paths. Note: No lineage or persisted artifacts.
