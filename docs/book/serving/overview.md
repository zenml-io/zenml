---
title: Pipeline Serving Overview
---

# Pipeline Serving Overview

## What Is Pipeline Serving?

- Purpose: Expose a ZenML pipeline as a low-latency service (e.g., via FastAPI) that executes steps on incoming requests and returns results.
- Value: Production-grade orchestration with simple capture options to balance latency, observability, and lineage.
- Modes by context: Batch outside serving (blocking), Realtime in serving (async), and pure in-memory serving for maximum speed.

## Quick Start

1) Define your pipeline
- Use your normal `@pipeline` and `@step` definitions.
- No serving-specific changes required.

2) Choose capture only when you need to change defaults
- You don’t need to set capture in most cases:
  - Batch (outside serving) is blocking.
  - Serving is async by default.
- Optional tweaks (typed API only):
  - Make it explicit: `@pipeline(capture=Capture())`
  - Pure in-memory serving: `@pipeline(capture=Capture(memory_only=True))`

3) Deploy the serving service with your preferred deployer and call the FastAPI endpoint.

## Capture Essentials

- Batch (outside serving)
  - Blocking publishes; full persistence as configured by capture toggles.

- Serving (inside serving)
  - Async publishes by default with an in‑process cache; low latency.

- Memory-only (serving only)
  - Pure in‑memory execution: no runs/steps/artifacts or server calls; maximum speed.
  - Outside serving, `memory_only=True` is ignored with a warning.

## Where To Configure Capture

- In code (typed only)
  - `@pipeline(capture=Capture(...))`
  - Options: `memory_only`, `code`, `logs`, `metadata`, `visualizations`, `metrics`

## Best Practices

- Most users (serving-ready)
  - `@pipeline(capture=Capture())`
  - Good balance of immediate response and production tracking.

- Maximum speed (no tracking at all)
  - `@pipeline(capture=Capture(memory_only=True))`
  - Great for tests, benchmarks, or hot paths where lineage is not needed.

- Compliance or rich lineage
  - Use Batch (outside serving) where publishes are blocking by default.

## FAQ (Essentials)

- Does serving always create pipeline runs?
  - Batch/Realtime: Yes.
  - Memory-only (Realtime with `memory_only=True`): No; executes purely in memory.

- Will serving block responses to flush tracking?
  - No. Serving is async by default and returns immediately.

- Is memory-only safe for production?
  - Yes for stateless, speed-critical paths. Note: No lineage or persisted artifacts.
