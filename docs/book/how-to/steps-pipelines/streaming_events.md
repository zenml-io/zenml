---
description: Publish live events from inside a step to subscribed clients.
---

# Streaming events

ZenML pipelines can push live events from inside a running step to any
subscriber listening on the server. This is the building block for LLM
token streaming, progress bars on long-running steps, real-time
dashboards, and any other "show what's happening right now" experience.

This page covers the **producer-side Python API** — calling
`zenml.streams.publish()` from inside a step. For enabling the feature on
the server and the HTTP/SSE consumer contract, see
[Live event streaming](../../getting-started/deploying-zenml/live-event-streaming.md).

{% hint style="info" %}
Streaming is **opt-in on the server** and **dormant by default** —
pipelines that don't call `zenml.streams.publish()` are unaffected, and
calls to `publish()` against a server with streaming disabled return
silently after the first 501 response.
{% endhint %}

{% hint style="warning" %}
Streaming is **best-effort transport** for live events. It is **not
durable storage** — events are capped, can be dropped under
backpressure, and disappear when the broker's retention window elapses.
Use [run metadata](../metadata/metadata.md) or
[artifacts](../artifacts/artifacts.md) for anything you need to persist.
{% endhint %}

## Publish from inside a step

```python
from zenml import step
from zenml.streams import publish

@step
def my_streaming_step() -> str:
    publish({"phase": "warmup"})
    for i in range(10):
        publish({"i": i, "msg": f"working on item {i}"})
    publish({"phase": "done"})
    return "ok"
```

`publish()` discovers the current pipeline run and step from the step
context — inside `@step`-decorated functions you don't need to pass any
handle. It **never blocks** the caller; events are queued and a background
thread ships them in small batches to the server.

## The `publish()` API

```python
from zenml.streams import publish, flush

publish(
    payload: Dict[str, Any],
    *,
    kind: str = "event",
    correlation_id: Optional[str] = None,  # logical-group tag
    index: Optional[int] = None,            # in-group ordering
) -> None
```

- `payload`: any JSON-serializable dict. **Capped at ~64 KiB per event
  on the wire** — bigger payloads are rejected by the server.
- `kind`: a free-form label clients can filter on. Must match
  `[A-Za-z0-9._-]{1,64}`. The kinds `end`, `gap`, `error`, `cursor`,
  and `system` are **reserved** for server-emitted control frames and
  will be rejected on `publish()`.
- `correlation_id` / `index`: opaque to ZenML — exposed to consumers
  unchanged so clients can group or order events that belong to one
  logical sub-flow (e.g., one `correlation_id` per LLM generation or per
  tool call). Consumers can filter by `correlation_id` on the SSE
  endpoint.

### Picking a `kind`

`kind` doubles as the SSE `event:` field on the wire — clients
`addEventListener("token", ...)` on it. A small enum of stable names that
your consumers code against is easier to maintain than free-form labels.
Common choices: `token` (LLM streaming), `progress` (step progress),
`status` (state changes), `log` (free-form log lines).

### Grouping with `correlation_id`

When a single step emits events for multiple parallel sub-flows — say an
agent that spawns several LLM generations in parallel — use
`correlation_id` to tag events so consumers can demultiplex them. The
field is opaque to ZenML (no validation, no interpretation); the only
contract is that consumers can filter on equality.

```python
publish({"text": chunk}, kind="token", correlation_id="gen-42", index=i)
```

A consumer can then subscribe with `?correlation_ids=gen-42` to receive
only that generation's tokens.

## `flush()` — wait for delivery

```python
from zenml.streams import flush

published = flush(timeout=2.0)  # bool: True if the queue drained
```

ZenML automatically flushes the publisher at step end, so most users
**don't need to call `flush()` directly**. Call it only when you want a
stronger guarantee that a specific event has reached the server before
some side effect — for example, posting a "ready" event right before
sending an external webhook that will trigger a consumer.

## Inside dynamic pipelines

Inside the body of a `@pipeline(dynamic=True)` (outside any `@step`),
`publish()` attributes events to the pipeline run but with no
`step_run_id` or `step_name`. See
[Dynamic Pipelines](dynamic_pipelines.md).

Calls to `publish()` from outside any pipeline or step context (e.g.,
module-level code, REPL, scripts) are silently dropped after a
`debug`-level log line — there's no run to attribute the event to.

## Producer-side limits

- Events are queued in-process with a **bounded buffer of 4 096 events**
  per Python process. Once full, the oldest queued event is dropped to
  make room — `publish()` itself never blocks.
- Per-event payload is capped at **64 KiB** on the wire envelope (this
  check runs locally at construction time, so oversize payloads fail
  fast inside `publish()` rather than after a wasted HTTP round-trip).
- The publisher batches up to **64 events per HTTP request** by default.
  Override with `ZENML_STREAM_PUBLISHER_BATCH_SIZE` if your producer
  needs higher throughput.
- After the server returns `501 Not Implemented` (streaming disabled),
  the publisher mutes itself for ~5 minutes before retrying — so a
  pipeline running against a server with streaming off pays at most one
  failed request per 5-minute window.
- Publishing requires `UPDATE` permission on the run.

For the wire format, delivery semantics, consumer protocol, and server
configuration knobs, see
[Live event streaming](../../getting-started/deploying-zenml/live-event-streaming.md).
