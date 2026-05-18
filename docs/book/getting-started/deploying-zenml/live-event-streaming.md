---
description: Enable live event streaming on the ZenML server and consume the HTTP/SSE feed.
---

# Live event streaming

ZenML can send events published from inside a pipeline run to any HTTP
client subscribed to that run. Use it for LLM token streaming, progress
updates, live dashboards, and similar cases where you need to surface
intermediate output from a running step.

This page covers operating streaming on the server: how to turn it on,
which broker to pick, how to consume the SSE feed, and the wire contract
clients code against. For the producer-side Python API (calling
`zenml.streaming.publish()` from a step), see
[Streaming Events](../../how-to/steps-pipelines/streaming_events.md).

{% hint style="warning" %}
Streaming is best-effort, not persistent storage. Events are size-capped,
can be dropped under load, and disappear when the broker's retention
window elapses. **Once an event is lost it is gone — there is no
secondary store, no replay endpoint, and no fallback.** If you need to
keep something, write it as run metadata or an artifact from the step.
{% endhint %}

## Enable streaming

Streaming is off by default. The single setting that enables it is
`stream_broker_implementation_source` on the server config (or
`streaming.streamBrokerImplementationSource` on the Helm chart). Until
that field is set, the streaming endpoints return `501 Not Implemented`,
producer-side `publish()` calls are dropped without sending HTTP, and
the server does not open a broker connection.

### Pick a broker

The Redis Streams broker
(`zenml.zen_server.streaming.brokers.redis_streams.RedisStreamsBroker`)
ships with ZenML. It requires Redis 5+ and the `redis` Python extra
(`pip install 'zenml[server-streaming]'`). It namespaces stream keys by
deployment ID so multiple ZenML servers can share a Redis cluster
without colliding.

### Configure with Helm

```yaml
server:
  streaming:
    streamBrokerImplementationSource: zenml.zen_server.streaming.brokers.redis_streams.RedisStreamsBroker
  environment:
    ZENML_REDIS_BROKER_URL: redis://my-redis.svc.cluster.local:6379/0
```

The chart installs an SSE-only Gateway API `HTTPRoute` rule that disables
Envoy's default 15-second request timeout for clients that send
`Accept: text/event-stream` against the `/api/v1/runs/` tree. Browsers'
`EventSource` and the ZenML server's own emitted frames match this
condition. Custom clients that send a quality-list `Accept` header fall
through to the default rule and are cut off at 15 seconds.

### Configure with environment variables

If you deploy without the chart, set the same field via env var:

```
ZENML_SERVER_STREAM_BROKER_IMPLEMENTATION_SOURCE=zenml.zen_server.streaming.brokers.redis_streams.RedisStreamsBroker
ZENML_REDIS_BROKER_URL=redis://...
```

Behind your own ingress, disable request timeouts and any response
buffering for the SSE path. The server emits `X-Accel-Buffering: no` and
`Cache-Control: no-cache, no-store, no-transform` to cover common
intermediaries, but you may need to set the same on your proxy.

### Server config reference

| Field (`ServerConfiguration`) | Helm key (`server.streaming.*`) | Default | Notes |
|---|---|---|---|
| `stream_broker_implementation_source` | `streamBrokerImplementationSource` | unset | Setting this enables streaming. |
| `streaming_heartbeat_seconds` | `heartbeatSeconds` | `30.0` | SSE heartbeat interval. |
| `streaming_max_subscribers_per_stream` | `maxSubscribersPerStream` | `100` | Maximum simultaneous subscribers per run. The 101st subscriber receives `503`. |
| `streaming_broadcaster_idle_grace_seconds` | `broadcasterIdleGraceSeconds` | `30.0` | How long the server keeps a stream's broker reader running after the last subscriber disconnects, so a quick reconnect does not have to re-establish it. |

### Redis settings

Connection settings are read from the shared `ZENML_REDIS_` prefix, so
the same Redis instance can be used by the streaming broker and by other
ZenML components that talk to Redis. Settings specific to the streaming
broker are read from `ZENML_REDIS_STREAMS_BROKER_` and override the
shared values when set.

| Variable | Default | Notes |
|---|---|---|
| `ZENML_REDIS_BROKER_URL` | — | `redis://...` or `rediss://...`. Required. |
| `ZENML_REDIS_MAX_CONNECTIONS` | `10` | Connection pool size. Increase if you expect many concurrent runs. Override per component with `ZENML_REDIS_STREAMS_BROKER_MAX_CONNECTIONS`. |
| `ZENML_REDIS_SOCKET_TIMEOUT` | `2.0` | Per-call timeout in seconds. |
| `ZENML_REDIS_STREAMS_BROKER_MAX_STREAM_LENGTH` | `10000` | Maximum entries retained per run (`XADD MAXLEN ~`). |
| `ZENML_REDIS_STREAMS_BROKER_STREAM_TTL_SECONDS` | `3600` | TTL on each run's stream, refreshed on every publish. |

At startup, the server runs a single connectivity check against the
broker. If the configured Redis URL is wrong or the host is unreachable,
the server fails to boot and reports the error, instead of returning
`503` on every later request.

## Consume the stream

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
[client SDK page](../../how-to/steps-pipelines/streaming_events.md) —
requires `UPDATE`.

### Browser

```javascript
const es = new EventSource(
  `/api/v1/runs/${runId}/events/stream`,
  { withCredentials: true }
);
es.addEventListener("event", (e) => console.log(JSON.parse(e.data)));
es.addEventListener("end", () => es.close());
```

`EventSource` automatically reconnects with the standard `Last-Event-ID`
header, so transient drops resume after the last received event (see
[Resuming after a disconnect](#resuming-after-a-disconnect)).

### Command line

```bash
curl -N -H "Accept: text/event-stream" \
  -H "Authorization: Bearer $ZENML_TOKEN" \
  "$ZENML_URL/api/v1/runs/$RUN_ID/events/stream"
```

`-N` disables curl's output buffering so frames arrive as the server
writes them.

## SSE wire format

Each frame the server emits has the form:

```
id: <broker-assigned id>
event: <kind>
data: <JSON-encoded StreamEvent>

```

Reserved event names:

| `event:` | Meaning |
|----------|---------|
| `event` (default) or any custom `kind` | A producer-published payload. `data` is the JSON-serialized `StreamEvent`. |
| `end` | The run has reached a terminal state. The server will close the connection. |
| `gap` | The subscriber may have missed events between the last `id` and now. Reasons: `outage` (broker reachability/reader error), `overflow` (per-subscriber queue full), `shutdown` (server is shutting down). |
| `error` | A transient server-side error. The client should reconnect with `Last-Event-ID`. |
| `cursor` | A frame the server emits for filtered-out events and for forward-compatible unknown frame types. Carries an `id:` so `Last-Event-ID` advances. `data` is `{}` for filtered events and `{"unknown_type": "<type>"}` for frames the server didn't recognize (useful for spotting producer-vs-server version mismatches). Clients can ignore both. |

Heartbeats arrive as comment frames (`: ping\n\n`) every
`streaming_heartbeat_seconds` (default 30 s) and require no client
handling. Comments do not dispatch events (they will not trigger any
`addEventListener` callback), which is why filtered or unknown frames
use `event: cursor` instead.

### Filtering

The SSE endpoint accepts three multi-value query parameters that
restrict which events are delivered. Each parameter accepts repeated
values; within a parameter the values are ORed, and the parameters
combine with AND. Filtered-out events still advance the server cursor
via `cursor` frames — clients can reconnect with `Last-Event-ID` and
will not see them replayed.

| Parameter | Matches | Example |
|---|---|---|
| `kinds` | `StreamEvent.kind` | `?kinds=token&kinds=progress` |
| `step_names` | `StreamEvent.step_name` (the invocation id of the step) | `?step_names=summarize` |
| `correlation_ids` | `StreamEvent.correlation_id` (producer-set sub-flow tag) | `?correlation_ids=gen-42` |

Combined:

```
GET /api/v1/runs/{run}/events/stream?kinds=token&step_names=summarize
```

returns only `token`-kind events from the `summarize` step.

### Resuming after a disconnect

The server honors the standard SSE `Last-Event-ID` request header on
reconnect. Browsers' `EventSource` sends it automatically. Other clients
should track the last `id:` they received and send it back to resume:

```
GET /api/v1/runs/{run}/events/stream
Last-Event-ID: <last id you received>
```

Clients that cannot set request headers (some embedded environments) can
use the `?since=<id>` query parameter as an equivalent — both specify
the starting cursor. If both are sent, the header wins.

If the cursor is older than the broker's retention window, the missing
events are not redelivered and the server does not signal that loss
happened. The next read returns whatever is still retained.

Subscribers can also attach to a run that has already terminated. The
server replays the broker's retained event history (up to the retention
TTL) and then closes with an `end` event. Once the TTL elapses the
history is gone and the subscribe returns just `end`.

**Lost events are unrecoverable.** Streaming is best-effort: events
never leave the broker for any durable store, and ZenML keeps no
secondary copy. Artifacts and run metadata persist the run's
*outcomes*, not the intermediate stream. Plan accordingly:

- If you need replay, write the relevant state as an artifact or
  metadata entry from the step.
- If your consumer maintains UI state derived from the stream
  (running aggregates, scrollback), design it to tolerate gaps —
  drop accumulated state and re-derive from new events going forward,
  rather than expecting to "fetch what you missed".

## Delivery semantics

| Property | What you get |
|----------|--------------|
| Ordering | Per-run, monotonic by broker id. |
| Duplicates | Within a single connection, each event id is delivered at most once. On reconnect with `Last-Event-ID`, the server resumes strictly after the last seen id, so events are not re-delivered. There is no producer-side retry on publish failure, so producers cannot introduce duplicates. Subscribers should still dedupe on event `id` defensively. |
| Loss | Events can be lost via producer-side queue overflow (4 096 per process), server-side publish failure (logged, not retried), broker-side `MAXLEN` truncation, retention TTL, or per-subscriber queue overflow. Per-subscriber overflow emits a `gap: overflow` frame; the other loss modes are silent. **Lost events are not recoverable from any other source** — ZenML keeps no durable copy of the stream. |
| Retention | `ZENML_REDIS_STREAMS_BROKER_STREAM_TTL_SECONDS` (default 1 h after the last publish). |
| Multi-replica | The broker delivers events across replicas, keyed by deployment id. |
| Persistence | None. Use run metadata or artifacts if you need durable storage. |

## Limits

- Per-event payload is limited to **64 KiB** on the wire envelope.
- The producer-side queue holds up to **4 096 events per process**. When
  full, the oldest queued event is dropped to make room.
- The broker stream is limited per run (default 10 000 entries).
  Subscribers that fall too far behind will silently miss the trimmed
  events — there is no wire-level signal for retention loss, and
  trimmed events are not stored anywhere recoverable.
- The per-run subscriber limit is `streaming_max_subscribers_per_stream`
  (default 100). The 101st connection receives `503 Service Unavailable`
  with `Retry-After: 5`.

## Troubleshooting

**SSE connections drop after 15 seconds behind an ingress.** Your proxy
is enforcing a request timeout. The bundled Helm chart configures the
Gateway API `HTTPRoute` to disable it for SSE; if you run a custom
ingress, do the same for `/api/v1/runs/.../events/stream` (or any path
where the request carries `Accept: text/event-stream`).

**Subscribers report missing events on reconnect.** The subscriber is
falling behind the broker's retention window. The missed events are
gone — they are not stored anywhere durable. Either reduce the producer
rate, raise `ZENML_REDIS_STREAMS_BROKER_MAX_STREAM_LENGTH`, or have the
subscriber drop accumulated stream-derived state on every `gap` and
re-derive from new events going forward.

**No events arrive.** Confirm streaming is enabled (the streaming
endpoints return something other than `501`), check the consumer has
`READ` on the run, and verify the producer is calling
`zenml.streaming.publish()` from inside a step or pipeline context. Calls
made outside such a context are dropped.

**`501 Not Implemented` on the streaming endpoints.**
`stream_broker_implementation_source` is unset. Once it is configured,
both the publish endpoint and the SSE endpoint become available. They
return `501` together when streaming is disabled.

**Server boot fails with "Stream broker startup probe failed".** The
configured broker cannot reach its backing store. For Redis, check
`ZENML_REDIS_BROKER_URL`, TLS settings, and network reachability from
the server pod.
