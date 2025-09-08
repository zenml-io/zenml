---
title: Capture & Execution Runtimes (Advanced)
---

# Capture & Execution Runtimes (Advanced)

This page explains how capture options map to execution runtimes and how to tune them for production serving.

## Execution Runtimes

- DefaultStepRuntime (Batch)
  - Standard ZenML execution: persists artifacts, creates runs and step runs, captures metadata/logs based on capture toggles.
  - Used outside serving.

- RealtimeStepRuntime (Serving, async by default)
  - Optimized for low latency with async server updates and an in‑process cache for downstream loads.
  - Tunables via env: `ZENML_RT_CACHE_TTL_SECONDS`, `ZENML_RT_CACHE_MAX_ENTRIES`, `ZENML_RT_ERR_REPORT_INTERVAL`, circuit breaker knobs (see Realtime Tuning page).

- MemoryStepRuntime (Serving with memory_only)
  - Pure in‑memory execution: no runs/steps/artifacts or server calls.
  - Inter‑step data is exchanged via in‑process handles.

## Capture API (typed only)
```python
from zenml.capture.config import Capture

# Serving async (default) – explicit but not required
@pipeline(capture=Capture())

# Serving memory-only (no DB/artifacts)
@pipeline(capture=Capture(memory_only=True))
def serve(...):
    ...
```

Options:
- `memory_only` (serving only): in‑process handoff; no persistence.
- Observability toggles (affect only observability, not dataflow):
  - `code`: include code/source/docstrings in metadata (default True)
  - `logs`: persist step logs (default True)
  - `metadata`: publish run/step metadata (default True)
  - `visualizations`: persist visualizations (default True)
  - `metrics`: emit runtime metrics (default True)

## Serving Defaults

- Serving uses the Realtime runtime and returns asynchronously by default.
- There is no `flush_on_step_end` knob; batch is blocking, serving is async.

## Validation & Behavior

- memory_only outside serving: ignored with a warning.
- Observability toggles never affect dataflow/caching, only what’s recorded.

## Step Operators & Remote Execution

Step operators and remote entrypoints derive behavior from context; no capture env propagation is required.

## Memory-Only Internals (for deeper understanding)

- Handle format: `mem://<run_id>/<upstream_step>/<output_name>`
- Memory runtime:
  - `resolve_step_inputs`: constructs handles from `run_id` + substitutions.
  - `load_input_artifact`: resolves handle to value from a thread-safe in-process store.
  - `store_output_artifacts`: stores outputs back to the store; returns new handles for downstream steps.
- No server calls; no runs or artifacts are created.

## Recipes

- Low-latency serving (default): `@pipeline(capture=Capture())`
- Memory-only (stateless service): `@pipeline(capture=Capture(memory_only=True))`

### Disable code capture (docstring/source)

Code capture affects metadata only (not execution). You can disable it via capture:

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

- Does `code: false` break step execution?
  - No. It only disables docstring/source capture. Steps still run normally.
- Can memory-only work with parallelism?
  - Memory-only is per-process. For multi-process/multi-container setups, use persistence for cross-process data.
