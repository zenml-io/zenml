---
description: Exporting logs to Grafana Loki.
---

# Grafana Loki Log Store

The Loki Log Store is a log store flavor that ships logs to [Grafana Loki](https://grafana.com/oss/loki/) and reads them back with LogQL, so pipeline logs are available both in the ZenML dashboard and in Grafana.

### When would you want to use it?

The Loki Log Store is a good fit when:

- You already run Loki or Grafana Cloud and want ML pipeline logs alongside the rest of your logs
- You want to keep logs on infrastructure you control, with a backend that is inexpensive to run
- You want to correlate pipeline logs with the metrics and traces already in your Grafana stack
- You want to build Grafana dashboards and alerts on top of pipeline logs

### How it works

Loki has ingested OpenTelemetry logs natively since version 3.0, so the write path is the generic one of the [OTEL Log Store](otel.md):

1. **Log capture**: All stdout, stderr, and Python logging output is captured during pipeline execution.

2. **OTLP export**: Log records are pushed to Loki's `/otlp/v1/logs` endpoint with ZenML-specific attributes attached.

3. **Storage shape**: Loki turns resource attributes into index labels and log attributes into per-entry structured metadata, replacing the dots of an attribute name with underscores. The ZenML attributes therefore end up as structured metadata under names like `zenml_log_id`.

4. **Log retrieval**: Reads go to Loki's `query_range` endpoint with a LogQL query that selects the service and narrows it to a single log stream, for example:

```
{service_name="zenml"} | zenml_log_id="<LOG_ID>"
```

### Requirements

- **Loki 3.0 or newer.** Older versions have no OTLP endpoint.
- **Structured metadata enabled**, which requires the TSDB index and schema `v13`. This is the default in recent versions, and it is what carries the ZenML attributes and the log level of each entry.

### How to use it

#### A self-hosted Loki

One address serves both ingestion and queries, so only the endpoint is needed:

```shell
zenml log-store register loki_logs \
    --flavor=loki \
    --endpoint=http://loki.observability.svc.cluster.local:3100/otlp/v1/logs

zenml stack register my_stack \
    -a my_artifact_store \
    -o default \
    -ls loki_logs \
    --set
```

#### A Loki in multi-tenant mode

```shell
zenml log-store register loki_logs \
    --flavor=loki \
    --endpoint=http://loki:3100/otlp/v1/logs \
    --tenant_id=ml-platform
```

#### Grafana Cloud

Grafana Cloud pushes and queries on different hosts, so both URLs are needed. The username is the numeric instance ID of your Loki stack, and the password is an access policy token with the `logs:write` and `logs:read` scopes.

```shell
zenml secret create grafana_cloud \
    --password=<YOUR_ACCESS_POLICY_TOKEN>

zenml log-store register loki_logs \
    --flavor=loki \
    --endpoint=https://logs-prod-eu-west-0.grafana.net/otlp/v1/logs \
    --query_url=https://logs-prod-eu-west-0.grafana.net \
    --username=<YOUR_INSTANCE_ID> \
    --password='{{grafana_cloud.password}}'
```

### Configuration options

| Parameter               | Default              | Description                                                          |
|-------------------------|----------------------|----------------------------------------------------------------------|
| `endpoint`              | _required_           | Loki's OTLP endpoint, ending in `/otlp/v1/logs`                      |
| `query_url`             | host of `endpoint`   | Base URL of the query API, without a path                            |
| `username`              | `None`               | Username for basic authentication, or the Grafana Cloud instance ID   |
| `password`              | `None`               | Password for basic authentication                                    |
| `api_key`               | `None`               | Token for bearer authentication, instead of basic authentication      |
| `tenant_id`             | `None`               | Tenant sent as `X-Scope-OrgID`                                       |
| `service_name`          | `"zenml"`            | Service name, which becomes the Loki stream label to query           |
| `service_version`       | ZenML version        | Service version attached to log records                              |
| `max_export_batch_size` | `500`                | Maximum batch size for exports                                       |
| `max_queue_size`        | `100000`             | Maximum queue size for the batch processor                           |
| `schedule_delay_millis` | `5000`               | Delay between batch exports (milliseconds)                           |
| `export_timeout_millis` | `15000`              | Timeout for each export batch (milliseconds)                         |

Whichever credentials are configured authenticate both ingestion and queries, so a secured Loki only needs to be configured once.

### Viewing logs

#### In the ZenML dashboard

Logs are fetched from Loki when viewing step details. Each fetch is a single range query that returns one page and the cursors for the pages on either side of it, so scrolling through a long step costs one query per page. Pages are read newest first, since that is where a failure usually is.

Loki has no continuation token, so a page is bounded by the timestamp of the entry at the edge of the previous page. That boundary is inclusive, which means the entries sitting exactly on it come back a second time and are dropped by their content, at nanosecond resolution.

Searching and filtering by level or time is done by Loki. A search term becomes a LogQL line filter, so unlike Datadog's token-based search it matches a substring anywhere in a message. A level filter becomes a comparison on the `severity_number` structured metadata. A page holds at most 5000 entries, which is Loki's default `max_entries_limit_per_query`.

{% hint style="info" %}
Only the service name is an index label; the log ID that identifies a single step's logs is structured metadata. Loki therefore reads the whole `service_name` stream over the time window of the run and filters it. This is fine at the scale of one pipeline run, but a Loki instance shared with high-volume production traffic under the same service name will make those reads slower. Giving ZenML its own `service_name` keeps that stream small.
{% endhint %}

#### In Grafana

Query the ZenML stream directly, narrowing it by whichever ZenML attribute is useful:

```
{service_name="zenml"} | zenml_pipeline_run_name="<YOUR_RUN_NAME>"
```

```
{service_name="zenml"} | zenml_step_run_name="my_training_step"
```

### Troubleshooting

#### Logs not appearing in Loki

1. Check that the endpoint ends in `/otlp/v1/logs`; ZenML posts to the URL exactly as configured.
2. Check whether Loki requires a tenant. It rejects a push with no `X-Scope-OrgID` in multi-tenant mode, and rejects one with a tenant header when authentication is disabled.
3. Loki refuses entries that are too old for its `reject_old_samples_max_age`, which matters when replaying logs of an older run.

#### Logs appear in Grafana but not in the ZenML dashboard

1. Confirm that structured metadata is enabled. Without it the ZenML attributes are dropped at ingestion, and no query can find the log stream they identify.
2. Confirm that `query_url` points at the query host, which is a different host to the ingestion one on Grafana Cloud.
3. Confirm that the credentials also grant read access; on Grafana Cloud the `logs:read` scope is separate from `logs:write`.

#### Every entry shows the same level

Severity is read from the per-entry structured metadata. A Loki configured to promote `severity_text` to a stream label instead does not affect this, but an ingestion path that drops structured metadata leaves ZenML with no severity to read, and it falls back to `INFO`.

For more information and a full list of configurable attributes, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-log_stores.html#zenml.log_stores.loki.loki_log_store).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
