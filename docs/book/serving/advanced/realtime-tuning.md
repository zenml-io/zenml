---
title: Realtime Runtime Tuning & Circuit Breakers
---

# Realtime Runtime Tuning & Circuit Breakers

This page documents advanced environment variables and metrics for tuning the Realtime runtime in production deployments. These knobs let you balance latency, throughput, and resilience under load.

## When To Use This

- High-QPS serving pipelines where latency and CPU efficiency matter
- Deployments needing stronger guardrails against cascading failures
- Teams instrumenting detailed metrics (cache hit rate, p95/p99 latencies)

## Environment Variables

Cache & Limits

- `ZENML_RT_CACHE_TTL_SECONDS` (default: `60`)
  - TTL for cached artifact values in seconds (in-process cache).
- `ZENML_RT_CACHE_MAX_ENTRIES` (default: `256`)
  - LRU cache entry bound to prevent unbounded growth.

Background Error Reporting

- `ZENML_RT_ERR_REPORT_INTERVAL` (default: `15`)
  - Minimum seconds between repeated background error logs (prevents log spam while maintaining visibility).

Circuit Breaker (async → inline fallback)

- `ZENML_RT_CB_ERR_THRESHOLD` (default: `0.1`)
  - Error rate threshold to open the breaker (e.g., `0.1` = 10%).
- `ZENML_RT_CB_MIN_EVENTS` (default: `100`)
  - Minimum number of publish events to evaluate before opening breaker.
- `ZENML_RT_CB_OPEN_SECONDS` (default: `300`)
  - Duration (seconds) to keep breaker open; inline publishing is used while open.

Notes

- Serving uses the Realtime runtime by default. Outside serving, batch runtime is used.

## Metrics & Observability

`RealtimeStepRuntime.get_metrics()` returns a snapshot of:

- Queue & Errors: `queued`, `processed`, `failed_total`, `queue_depth`
- Cache: `cache_hits`, `cache_misses`, `cache_hit_rate`
- Latency (op publish): `op_latency_p50_s`, `op_latency_p95_s`, `op_latency_p99_s`
- Config: `ttl_seconds`, `max_entries`

Recommendation

- Export metrics to your telemetry system (e.g., Prometheus) and alert on:
  - Rising `failed_total` and sustained `queue_depth`
  - Low `cache_hit_rate`
  - High `op_latency_p95_s` / `op_latency_p99_s`

## Recommended Production Defaults

- Start conservative, then tune based on SLOs:
  - `ZENML_RT_CACHE_TTL_SECONDS=60`
  - `ZENML_RT_CACHE_MAX_ENTRIES=256`
  - `ZENML_RT_ERR_REPORT_INTERVAL=15`
  - `ZENML_RT_CB_ERR_THRESHOLD=0.1`
  - `ZENML_RT_CB_MIN_EVENTS=100`
  - `ZENML_RT_CB_OPEN_SECONDS=300`

## Runbook (Common Scenarios)

- High background errors:
  - Check logs for circuit breaker events. If open, runtime will publish inline. Investigate upstream store or network failures.
  - Consider temporarily reducing load or increasing `ZENML_RT_CB_OPEN_SECONDS` while recovering.

- Rising queue depth / latency:
  - Verify artifact store and API latency.
  - Reduce cache TTL or size to reduce memory pressure; consider scaling workers.

- Low cache hit rate:
  - Check step dependencies and cache TTL; ensure downstream steps run in the same process to benefit from warm cache.
