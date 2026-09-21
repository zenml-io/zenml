---
description: Storing and querying pipeline logs with Grafana Loki.
---

# Grafana Loki Log Store

The Loki Log Store exports logs to Grafana Loki and queries them with LogQL. Use it to view pipeline logs in ZenML alongside the logs in your Grafana dashboards.

### Requirements

Use Loki 3.0 or newer with OTLP ingestion and structured metadata enabled. Structured metadata requires the TSDB index and schema `v13` or newer. See Loki's [OpenTelemetry ingestion guide](https://grafana.com/docs/loki/latest/send-data/otel/) and [structured metadata requirements](https://grafana.com/docs/loki/latest/get-started/labels/structured-metadata/).

The flavor is built into ZenML; no integration installation is required. Both the pipeline environment and the ZenML server need access to the appropriate ingestion or query endpoint.

### How to use it

#### Self-hosted Loki

Register the full OTLP logs endpoint. For a deployment that accepts writes and queries at the same address, ZenML derives the query URL automatically:

```shell
zenml log-store register loki_logs \
    --flavor=loki \
    --endpoint=http://loki.observability.svc.cluster.local:3100/otlp/v1/logs

zenml stack register my_stack \
    -a my_artifact_store \
    -o default \
    --log_store loki_logs \
    --set
```

For a multi-tenant deployment, add `--tenant_id=<TENANT_ID>`. It is sent as `X-Scope-OrgID` on writes and queries.

#### Grafana Cloud or authenticated Loki

For basic authentication, configure both `username` and `password`. On Grafana Cloud, use your stack's instance ID and an access policy token with log read and write permissions. Copy the ingestion and query endpoints from your stack's connection details:

```shell
zenml secret create grafana_cloud \
    --password=<YOUR_ACCESS_POLICY_TOKEN>

zenml log-store register loki_logs \
    --flavor=loki \
    --endpoint=<OTLP_LOGS_ENDPOINT> \
    --query_url=<LOKI_QUERY_BASE_URL> \
    --username=<YOUR_INSTANCE_ID> \
    --password='{{grafana_cloud.password}}'
```

For a gateway that uses bearer authentication, configure `api_key` instead of `username` and `password`. Store the token in a ZenML secret and pass its reference to `--api_key`.

### Configuration options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `endpoint` | _required_ | Full OTLP ingestion URL, ending in `/otlp/v1/logs`. |
| `query_url` | Derived from `endpoint` | Query API base URL, without `/loki/api/v1/query_range`. Set it explicitly when queries use a different address. |
| `username` | `None` | Basic authentication username. Requires `password`. |
| `password` | `None` | Basic authentication password or access policy token. |
| `api_key` | `None` | Bearer token; cannot be combined with basic authentication. |
| `tenant_id` | `None` | Tenant identifier for `X-Scope-OrgID`. |
| `service_name` | `"zenml"` | Service name used to select the Loki stream. |

The flavor also supports the [OpenTelemetry log store's export settings](otel.md#configuration-options), including batching, compression, and TLS certificates. Authentication credentials are used for both ingestion and queries.

### Viewing logs

Loki supports server-side filtering and returns one batch per query. A fetch reads the newest entries by default; use `start="oldest"` to read from the other end. Each batch is returned in chronological order.

The default batch size is 1000 and the maximum is 5000, subject to `ZENML_LOGS_MAX_ENTRIES_PER_REQUEST`. If your Loki deployment sets a lower `max_entries_limit_per_query`, pass a matching `limit`.

Loki's `query_range` API has no native continuation token. Both `before` and `after` are always unset, and passing either cursor raises `ValueError` in the SDK or returns HTTP `400`. Narrow the filters or time window to retrieve a smaller batch; use the returned entries for client-side pagination.

The filters run in Loki:

- `search` performs a case-sensitive substring match on the original log message through a LogQL `|=` line filter.
- `level` is a minimum severity, so `WARNING` includes warnings and errors.
- `since` and `until` bound the query by time. Both bounds are inclusive.

When omitted, the time window runs from the log stream's creation time to the current UTC time.

Using the `log_store` and `logs` objects from the [Python SDK example](README.md#python-sdk):

```python
from zenml.models import LogsEntriesFilter

batch = log_store.fetch(
    logs_model=logs,
    limit=100,
    filter_=LogsEntriesFilter(level="WARNING", search="training"),
)
for entry in batch.items:
    print(entry.message)
```

Entries have stable UUIDs derived from Loki's timestamp, message, and labels and metadata. Identical entries with the same values share an ID because Loki does not expose a unique event ID.

#### In Grafana

ZenML attributes use underscores in Loki. Query a run or step directly with LogQL:

```logql
{service_name="zenml"} | zenml_pipeline_run_name="<YOUR_RUN_NAME>"
```

```logql
{service_name="zenml"} | zenml_step_run_name="my_training_step"
```

Keep ZenML's `service_name` distinct from unrelated high-volume services. Loki uses it as an index label and filters the ZenML log stream ID from structured metadata.

### Troubleshooting

If logs do not appear, check that the ingestion endpoint ends in `/otlp/v1/logs`, structured metadata is enabled, and the credentials and tenant allow writes. Loki can also reject records outside its configured age limits.

If logs appear in Grafana but not in ZenML, check the query URL, read permissions, and `service_name`. Preserve the `zenml_*` and severity metadata during ingestion so ZenML can identify and filter the stream.

If large batches time out and Loki reports a gRPC message-size error, reduce `limit` or adjust Loki's [gRPC message-size limits](https://grafana.com/docs/loki/latest/operations/troubleshooting/troubleshoot-operations/).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
