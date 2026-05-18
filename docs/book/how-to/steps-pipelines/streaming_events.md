---
description: Publish live events from inside a step to subscribed clients.
---

# Streaming events

ZenML pipelines can send live events from inside a running step to any
subscriber listening on the server. Use it for LLM token streaming,
progress updates from long-running steps, real-time dashboards, and
similar cases where you need to surface intermediate output before the
step returns.

This page covers the producer-side Python API — calling
`zenml.streaming.publish()` from inside a step. For enabling streaming on
the server and the HTTP/SSE wire contract, see
[Live event streaming](../../getting-started/deploying-zenml/live-event-streaming.md).

{% hint style="info" %}
Streaming is off by default and must be enabled on the server. Pipelines
that don't call `zenml.streaming.publish()` are unaffected. Once a server
returns `501 Not Implemented`, the producer self-mutes for the rest of
the process and further `publish()` calls return without sending HTTP.
{% endhint %}

{% hint style="warning" %}
Streaming is best-effort, not persistent storage. Events are size-capped,
can be dropped under load, and disappear when the broker's retention
window elapses. **Once an event is lost it's gone — ZenML keeps no
secondary copy.** If you need to keep something, write it as
[run metadata](../metadata/metadata.md) or an
[artifact](../artifacts/artifacts.md).
{% endhint %}

## Publish from inside a step

```python
from zenml import step
from zenml.streaming import publish

@step
def my_streaming_step() -> str:
    publish({"phase": "warmup"})
    for i in range(10):
        publish({"i": i, "msg": f"working on item {i}"})
    publish({"phase": "done"})
    return "ok"
```

`publish()` reads the current pipeline run and step from the step
context — inside `@step`-decorated functions you don't need to pass any
handle. The call does not block; events are queued and a background
thread sends them to the server in small batches.

## The `publish()` API

```python
from zenml.streaming import publish, flush

publish(
    payload: Dict[str, Any],
    *,
    kind: str = "event",
    correlation_id: Optional[str] = None,
    index: Optional[int] = None,
) -> None
```

- `payload`: any JSON-serializable dict. Each event is limited to 64 KiB
  on the wire envelope; the check runs inside `publish()` so oversize
  payloads fail locally rather than after an HTTP round-trip.
- `kind`: a free-form label that clients can filter on.
- `correlation_id` / `index`: opaque to ZenML — passed through to
  consumers unchanged so clients can group or order events that belong
  to the same logical sub-flow (for example, one `correlation_id` per
  LLM generation, or one per tool call). Consumers can filter by
  `correlation_id` on the SSE endpoint.

### Picking a `kind`

`kind` is also the SSE `event:` field on the wire — clients subscribe
with `addEventListener("token", ...)`. A small set of stable names that
your consumers code against is easier to maintain than ad-hoc labels.
Common choices: `token` (LLM streaming), `progress` (step progress),
`status` (state changes), `log` (free-form log lines).

### Grouping with `correlation_id`

When a single step emits events for multiple parallel sub-flows — for
example, an agent that issues several LLM generations in parallel — use
`correlation_id` to tag each event so consumers can separate them. The
field is opaque to ZenML (no validation, no interpretation); the only
contract is that consumers can filter on equality.

```python
publish({"text": chunk}, kind="token", correlation_id="gen-42", index=i)
```

A consumer can then subscribe with `?correlation_ids=gen-42` to receive
only that generation's tokens.

## `flush()` — wait for delivery

```python
from zenml.streaming import flush

published = flush(timeout=2.0)  # True if the queue drained
```

A background worker drains the queue continuously, and `atexit` catches
process termination, so most users don't need to call `flush()`. Call it
when you need to be sure a specific event has reached the server before
doing something else — for example, posting a "ready" event right
before sending an external webhook whose target will consume the
stream.

## Inside dynamic pipelines

Inside the body of a `@pipeline(dynamic=True)` (outside any `@step`),
`publish()` attributes events to the pipeline run with no `step_run_id`
or `step_name`. See [Dynamic Pipelines](dynamic_pipelines.md).

Calls to `publish()` made outside any pipeline or step context (for
example, module-level code, a REPL, scripts) are dropped after a
`debug`-level log line — there is no run to attribute the event to.

## Producer-side limits

- The in-process queue holds up to **4 096 events** per Python process.
  Once full, the oldest queued event is dropped to make room — `publish()`
  itself never blocks.
- Each event payload is limited to **64 KiB** on the wire envelope.
- The publisher batches up to **64 events per HTTP request** by default.
  Override with `ZENML_STREAM_PUBLISHER_BATCH_SIZE` if your producer
  needs higher throughput. Keep it ≤ 1 000 (the server's batch cap);
  larger values cause every send to fail validation server-side.
- Publishing requires `UPDATE` permission on the run.

For the wire format, delivery semantics, the consumer protocol, and
server configuration, see
[Live event streaming](../../getting-started/deploying-zenml/live-event-streaming.md).
