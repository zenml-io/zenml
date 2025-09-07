## Beta: Unified Serving Capture, Memory-Only Isolation, and Realtime Hardening

This PR delivers a focused, pragmatic refactor to make serving reliable and easy to reason about for a beta release. It simplifies capture configuration to a single typed `Capture`, unifies the execution path, introduces memory-only isolation, and hardens the realtime runtime with bounded resources and better shutdown behavior.

### Summary

- Collapse capture to a single typed API: `Capture(memory_only, code, logs, metadata, visualizations, metrics)`.
- Canonical capture fields on deployments; StepLauncher reads only those (no env/dict overrides).
- Serving request parameters are merged safely (allowlist + light validation + size caps); logged.
- Memory-only serving mode: truly no runs/artifacts/log writes; in-process handoff with per-request isolation.
- Realtime runtime: bounded queue, safe cache sweep, circuit-breaker maintained, improved shutdown and metrics.
- Defensive artifact writes: validation and minimal retries/backoff; fail fast on partial responses.
- In-code TODOs added for post-beta roadmap (transactions, multi-worker/async publishing, monitoring).

### Motivation

- Eliminate confusing capture modes and env overrides in code paths.
- Ensure serving is fast (async by default) and memory-only mode never touches DB/FS.
- Prevent cross-request contamination in memory-only; bound resource usage under load.
- Provide clear logs and metrics for diagnosis; pave the way for production hardening.

### Key Behavioral Changes

- Pipeline code uses a single `Capture` type; dicts/strings disallowed in code paths.
- Serving merges request parameters only from a declared allowlist; oversized/mismatched params are dropped with warnings.
- Memory-only serving executes fully in-process (no runs/artifacts), with explicit logs; step logs disabled to avoid FS writes.
- Realtime runtime backgrounds publishing with a bounded queue; if the queue is full, events are processed inline.

### File-Level Changes (Selected)

- Capture & Compiler
  - `src/zenml/capture/config.py`: Single `Capture` dataclass; removed BatchCapture/RealtimeCapture/CapturePolicy.
  - `src/zenml/config/compiler.py`: Normalizes typed capture into canonical deployment fields.
  - `src/zenml/models/v2/core/pipeline_deployment.py`: Adds canonical capture fields to deployment models.
  - `src/zenml/zen_stores/schemas/pipeline_deployment_schemas.py`: Adds DB columns for canonical capture fields.

- Orchestrator
  - `src/zenml/orchestrators/step_launcher.py`:
    - Uses canonical fields and serving context.
    - Adds `_validate_and_merge_request_params` (allowlist + type coercion + size caps).
    - Disables logs in memory-only; avoids FS cleanup for `memory://` URIs.
  - `src/zenml/orchestrators/run_entity_manager.py`: In-memory step_run stub with minimal config (`enable_*`, `substitutions`).
  - `src/zenml/orchestrators/utils.py`: Serving context helpers and docstrings; removed request-level override plumbing.

- Execution Runtimes
  - `src/zenml/execution/step_runtime.py`:
    - `MemoryStepRuntime`: instance-scoped store/locks; per-run cleanup; no globals.
    - `DefaultStepRuntime.store_output_artifacts`: defensive batch create (retries/backoff), response count validation; TODO for server-side atomicity.
  - `src/zenml/execution/realtime_runtime.py`:
    - Bounded queue (maxsize=1024), inline fallback on Full.
    - Safe cache sweep (snapshot + safe pop, small time budget).
    - Shutdown logs final metrics and warns on non-graceful termination; TODOs for thread-pool or async migration and metrics export.

- Serving Service & Docs
  - `src/zenml/deployers/serving/service.py`: Serving context handling; parameter exposure; cleanup.
  - `docs/book/serving/*`: Updated to single Capture, serving async default, memory-only warning/behavior.
  - `examples/serving/README.md`: Updated to reflect new serving model; memory-only usage.

### Configuration & Tuning

- Serving mode is inferred by context (batch vs. serving). No per-request capture overrides.
- Realtime runtime tuning via env:
  - `ZENML_RT_CACHE_TTL_SECONDS` (default 60), `ZENML_RT_CACHE_MAX_ENTRIES` (default 256)
  - `ZENML_RT_ERR_REPORT_INTERVAL` (default 15), circuit breaker envs unchanged
- Memory-only: ignored outside serving with a warning.

### Testing & Validation

- Unit
  - Request parameter validation: allowlist, size caps, type coercion.
  - Memory runtime isolation: per-instance store; no cross-contamination.
  - Realtime runtime: queue Full → inline fallback; race-free cache sweep; shutdown metrics.
  - Defensive artifact writes: retries/backoff; mismatch detection.

- Manual
  - Memory-only serving: no `/runs` or `/artifact_versions` calls; explicit log: `[Memory-only] … in-process handoff (no runs/artifacts)`.
  - Serving async default: responses return immediately; background updates proceed.

### Risk & Mitigations

- Request param merge: now restricted by allowlist/size/type; unknowns dropped with warnings.
- Memory-only: per-request isolation and no FS/DB writes; logs disabled to avoid side effects.
- Realtime: bounded queue with inline fallback; circuit breaker remains in place.
- Artifact writes: fail fast rather than proceed with partial results; TODO for server-side atomicity.

### In-Code TODOs (Post-Beta Roadmap)

- Realtime runtime publishing:
  - Either thread pool (ThreadPoolExecutor) workers or asyncio runtime once client has async publish calls and we want async serving.
  - Preserve bounded backpressure and orderly shutdown.
- Request parameter schema derived from entrypoint annotations; add total payload size caps and strict mode.
- Server-side transactional/compensating semantics for artifact writes; adopt idempotent, category-aware retries.
- Metrics export to Prometheus; per-worker metrics; worker liveness/health signals; process memory watchdog.

### How to Review

- Focus on StepLauncher (param merge, memory-only flags) and runtimes (Memory/Realtime).
- Verify serving behavior in logs; check that memory-only path never touches DB/FS.
- Review TODOs in code for future milestones.

### Rollout

- Tag as beta and monitor runtime metrics (`queue_depth`, `failed_total`, `cache_hit_rate`, `op_latency_p95_s`).
- Scale by increasing HTTP workers and replicas; memory-only is fastest for prototypes.
- Provide guidance on cache sizing and memory usage in docs.

