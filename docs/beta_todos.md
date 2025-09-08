# Beta Hardening TODOs

This is a living checklist for post‑beta hardening. All beta blockers are already implemented; the items below are for production readiness and scale.

## Serving Runtime & Publishing

- Multi‑worker scaling per process
  - Option A (threads): Add a small ThreadPoolExecutor consuming the existing bounded queue; preserve backpressure and flush semantics.
  - Option B (async): Introduce an asyncio loop + asyncio.Queue + async workers, once client/publish calls have async variants and we opt into async serving.
  - Keep bounded queue, inline fallback on Full, and orderly shutdown (join/cancel with timeout).

- Backpressure & batching
  - Tune queue maxsize defaults; expose env knob `ZENML_RT_QUEUE_MAXSIZE`.
  - Optional: micro‑batch compatible events for fewer round‑trips.

- Circuit breaker refinements
  - Distinguish network vs. logical errors for better decisions.
  - Add optional cool‑down logs with guidance.

## Artifact Write Semantics

- Server‑side atomicity / compensation
  - Align with server to provide atomic batch create or server‑side compensation.
  - Client: switch from best‑effort retries to idempotent, category‑aware retries once server semantics are defined.
  - Document consistency guarantees and failure behavior.

## Request Parameter Schema & Safety

- Parameter schema from entrypoint annotations
  - Generate/derive expected types from pipeline entrypoint annotations (or compiled schema) rather than inferring from defaults.
  - Add total payload size cap; add per‑type caps (e.g., list length, dict depth).
  - Optional: strict mode that rejects unknown params rather than dropping.

## Monitoring, Metrics, Health

- Metrics enrichment
  - Export runtime metrics to Prometheus (queue depth, cache hit rate, error rate, op latency histograms).
  - Add per‑worker metrics if multi‑worker is enabled.

- Health/liveness
  - Expose background worker liveness/health via the service.
  - Add simple self‑check endpoints and document alerts.

## Memory & Resource Management

- Process memory monitoring / limits
  - Add process memory watchdog and log warnings; document recommended container limits.
  - Add a user‑facing docs note about caching large artifacts and tuning `max_entries` accordingly.

## Operational Docs & UX

- Serving docs
  - Add a prominent warning about memory usage for large cached artifacts and sizing `ZENML_RT_CACHE_MAX_ENTRIES`.
  - Add examples for scaling processes/replicas and interpreting metrics.

## Notes (Implemented in Beta)

- Request param allowlist / type coercion / size caps
- Memory‑only isolation (instance‑scoped) and cleanup
- Bounded queue with inline fallback; race‑free cache sweep
- Graceful shutdown with timeout and final metrics
- Defensive artifact write behavior with minimal retries and response validation
