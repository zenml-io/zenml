---
description: Enable the streaming subsystem on the ZenML server and consume the HTTP/SSE feed.
---

# Live event streaming

ZenML can fan out events published from inside a pipeline run to any HTTP
client subscribed to that run — the building block for LLM token streaming,
progress bars, live dashboards, and any other "show what's happening right
now" experience.

This page covers **operating** the streaming subsystem: how to turn it on,
which broker to pick, how to consume the SSE feed, and the wire contract
clients code against. For the producer-side Python API (calling
`zenml.streams.publish()` from a step), see
[Streaming Events](../../how-to/steps-pipelines/streaming_events.md).

{% hint style="warning" %}
Streaming is **best-effort, ephemeral transport**. It is **not durable
storage** — events are capped, can be dropped under backpressure, and
disappear when the broker's retention window elapses. Use run metadata or
artifacts for anything you need to persist.
{% endhint %}

## Enabling streaming

Streaming is **opt-in** and **dormant by default**. The single switch that
turns it on is `stream_broker_implementation_source` on the server config
(or `streaming.streamBrokerImplementationSource` on the Helm chart). Until
that field is set, the streaming endpoints return `501 Not Implemented`,
producer-side `publish()` calls are silently dropped, and no broker
connection is opened.

### Pick a broker

Two implementations ship with ZenML:

| Broker | Class source | Use when |
|---|---|---|
| In-memory | `zenml.zen_server.streaming.brokers.memory.InMemoryBroker` | Single-replica deployments, local dev, demos. Events live in the server process and vanish on restart. |
| Redis Streams | `zenml.zen_server.streaming.brokers.redis_streams.RedisStreamsBroker` | Multi-replica deployments. Requires Redis 5+ and the `redis` Python extra (`pip install 'zenml[server-streaming]'`). |

The in-memory broker has zero infrastructure cost but does not fan events
across server replicas — a producer hitting one replica and a consumer
attached to another won't see each other's traffic. The Redis broker keys
streams by deployment ID so multiple ZenML servers can share a Redis
cluster without colliding.

### Configure with Helm

```yaml
server:
  streaming:
    streamBrokerImplementationSource: zenml.zen_server.streaming.brokers.redis_streams.RedisStreamsBroker
  environment:
    ZENML_REDIS_BROKER_URL: redis://my-redis.svc.cluster.local:6379/0
```

The chart installs an SSE-only Gateway-API `HTTPRoute` rule that disables
Envoy's 15-second wall-clock request timeout for clients sending
`Accept: text/event-stream` against the `/api/v1/runs/` tree. Browsers'
`EventSource` and the ZenML server's emitted frames qualify automatically;
hand-rolled clients that send a quality-list `Accept` header fall through
to the default rule and get capped at 15 s.

### Configure with environment variables

If you deploy without the chart, set the same field via env var:

```
ZENML_SERVER_STREAM_BROKER_IMPLEMENTATION_SOURCE=zenml.zen_server.streaming.brokers.redis_streams.RedisStreamsBroker
ZENML_REDIS_BROKER_URL=redis://...
```

Behind your own ingress, make sure to disable request timeouts and any
response buffering for the SSE path. The server emits `X-Accel-Buffering:
no` and `Cache-Control: no-cache, no-store, no-transform` to cover common
intermediaries, but you may need to mirror that on your proxy.

### Server config reference

| Field (`ServerConfiguration`) | Helm key (`server.streaming.*`) | Default | Notes |
|---|---|---|---|
| `stream_broker_implementation_source` | `streamBrokerImplementationSource` | unset | Setting this enables streaming. |
| `streaming_heartbeat_seconds` | `heartbeatSeconds` | `30.0` | SSE heartbeat / idle keepalive interval. |
| `streaming_max_consumers_per_stream` | `maxConsumersPerStream` | `100` | Hard cap per run; the 101st gets `503`. |
| `streaming_hub_idle_grace_seconds` | `hubIdleGraceSeconds` | `30.0` | How long the hub keeps a stream's reader alive after the last consumer disconnects. |

### Redis-specific settings (env vars)

| Variable | Default | Notes |
|---|---|---|
| `ZENML_REDIS_BROKER_URL` | — | `redis://...` or `rediss://...`. Required. |
| `ZENML_REDIS_MAX_CONNECTIONS` | `10` | Pool size. Bump if you expect many concurrent runs. |
| `ZENML_REDIS_SOCKET_TIMEOUT` | `2.0` | Per-call timeout in seconds. |
| `ZENML_REDIS_STREAMS_BROKER_MAX_STREAM_LENGTH` | `10000` | Per-run entry cap (`XADD MAXLEN ~`). |
| `ZENML_REDIS_STREAMS_BROKER_STREAM_TTL_SECONDS` | `3600` | TTL refreshed on every publish. |

A startup connectivity probe runs against the broker as part of server
initialization — a misconfigured Redis URL or unreachable host fails the
server boot loudly rather than 503-ing every request later.

## Consuming the stream

Streams are exposed as
[Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
on:

```
GET /api/v1/runs/{pipeline_run_id}/events/stream
Accept: text/event-stream
Authorization: Bearer <token>
```

Consuming requires `READ` permission on the run (the same permission as
viewing it in the dashboard). Publishing — covered on the
[client SDK page](../../how-to/steps-pipelines/streaming_events.md) — needs
`UPDATE`.

### Browser

```javascript
const es = new EventSource(
  `/api/v1/runs/${runId}/events/stream`,
  { withCredentials: true }
);
es.addEventListener("event", (e) => console.log(JSON.parse(e.data)));
es.addEventListener("end", () => es.close());
```

`EventSource` automatically reconnects with the standard
`Last-Event-ID` header, so transient drops resume where they left off (see
[Resuming after a disconnect](#resuming-after-a-disconnect)).

### Command line

```bash
curl -N -H "Accept: text/event-stream" \
  -H "Authorization: Bearer $ZENML_TOKEN" \
  "$ZENML_URL/api/v1/runs/$RUN_ID/events/stream"
```

`-N` disables curl's output buffering so frames arrive as they're written.

## SSE wire format

Each frame the server emits looks like:

```
id: <broker-assigned id>
event: <kind>
data: <JSON-encoded StreamEvent>

```

Well-known event names:

| `event:` | Meaning |
|----------|---------|
| `event` (default) or any custom `kind` | A producer-published payload. `data` is the JSON-serialized `StreamEvent`. |
| `end` | The run has reached a terminal state; the server will close the connection. |
| `gap` | The consumer may have missed events between the last `id` and now (reasons: `truncated`, `outage`, `overflow`, `broker_error`, `shutdown`). |
| `error` | A transient server-side error. The client should reconnect with `Last-Event-ID`. |
| `cursor` | No-payload frame the server emits for filtered-out events or forward-compatible unknown frame types. Carries an `id:` so `Last-Event-ID` advances; clients can ignore the `data`. |

Heartbeats arrive as comment frames (`: ping\n\n`) every
`streaming_heartbeat_seconds` (default 30 s) and require no client
handling. Comments don't dispatch events (so they won't trigger any
`addEventListener` callback), which is why filtered/unknown frames use
`event: cursor` instead.

### Filtering

The SSE endpoint accepts three multi-value query parameters that restrict
which events are delivered. Each parameter accepts repeated values; within
a parameter the values are ORed, and the parameters combine as AND.
Filtered-out events still advance the server cursor via `cursor` frames
— clients can safely reconnect with `Last-Event-ID` and won't see them
replayed.

| Parameter | Matches | Example |
|---|---|---|
| `kinds` | `StreamEvent.kind` | `?kinds=token&kinds=progress` |
| `step_names` | `StreamEvent.step_name` (the invocation id of the step) | `?step_names=summarize` |
| `correlation_ids` | `StreamEvent.correlation_id` (producer-set sub-flow tag) | `?correlation_ids=gen-42` |

Combined:

```
GET /api/v1/runs/{run}/events/stream?kinds=token&step_names=summarize
```

delivers only `token`-kind events from the `summarize` step.

### Resuming after a disconnect

The server honours the standard SSE `Last-Event-ID` request header on
reconnect. Browsers' `EventSource` sends it automatically; other clients
should track the last `id:` they received and send it back to resume:

```
GET /api/v1/runs/{run}/events/stream
Last-Event-ID: <last id you received>
```

Clients that can't set request headers (some embedded environments) can
use the `?since=<id>` query parameter as an equivalent — both specify the
starting cursor. If both are provided, the header wins.

If too much time has passed and the event has been trimmed from the
broker, the server emits a `gap: truncated` frame instead of silently
skipping events. Consumers should treat any `gap` as a signal to re-fetch
state from authoritative sources (artifacts, run metadata) for the
affected window.

## Delivery semantics

| Property | What you get |
|----------|--------------|
| Ordering | Per-run, monotonic by broker id. |
| Duplicates | At-most-once across a single connection; consumers should be idempotent across reconnects. On the Redis broker, a pipelined publish that partially fails can also deliver a subset of a batch twice on producer retry — design consumers to dedupe on event `id`. |
| Loss | Best-effort. Events can be dropped by producer-side backpressure (queue cap is 4 096 per process) or by broker-side cap (default 10 000 entries per run). |
| Retention | Redis: `ZENML_REDIS_STREAMS_BROKER_STREAM_TTL_SECONDS` (default 1 h after the last publish). In-memory: until the hub closes the session (`streaming_hub_idle_grace_seconds`, default 30 s after the last consumer leaves). |
| Multi-replica | Redis broker fans out across replicas via the deployment id. In-memory works only on a single-replica deployment. |
| Persistence | None. Use run metadata or artifacts if you need durable storage. |

## Limits

- Per-event payload is capped at **64 KiB** on the wire envelope.
- The publisher-side queue is bounded at **4 096 events per process** —
  events are dropped (oldest-first) if a step publishes faster than the
  server can ingest.
- The broker stream is **capped per run** (default 10 000 entries on both
  brokers). Consumers that fall too far behind will see a `gap: truncated`
  frame.
- The `InMemoryBroker` is single-replica only. Multi-replica deployments
  must use the Redis broker.
- Per-run consumer cap is `streaming_max_consumers_per_stream` (default
  100); the 101st connection gets `503 Service Unavailable` with
  `Retry-After: 5`.

## Troubleshooting

**SSE connections drop after 15 seconds behind an ingress.** Your proxy
is enforcing a request timeout. The bundled Helm chart configures the
Gateway API `HTTPRoute` to disable it for SSE; if you run a custom ingress,
mirror that for `/api/v1/runs/.../events/stream` (or any path with `Accept:
text/event-stream`).

**Clients see `gap: truncated` repeatedly.** The consumer is falling
behind the broker's retention. Either reduce the producer rate, bump
`ZENML_REDIS_STREAMS_BROKER_MAX_STREAM_LENGTH`, or have the consumer drop
stale state and re-fetch on every `gap`.

**No events ever arrive.** Confirm streaming is enabled (`GET
/api/v1/info` will not 501 the streaming endpoints), check the consumer
has `READ` on the run, and verify the producer is actually publishing —
`zenml.streams.publish()` calls outside a step or pipeline context are
silently dropped.

**`501 Not Implemented` on the streaming endpoints.**
`stream_broker_implementation_source` is unset. Once configured, both the
publish and SSE endpoints become available; both 501 in lockstep.

**Server boot fails with "Stream broker startup probe failed".** The
configured broker can't reach its backing store — for Redis, check
`ZENML_REDIS_BROKER_URL`, TLS settings, and network reachability from the
server pod.
