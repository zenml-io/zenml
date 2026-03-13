---
description: Exporting and retrieving logs with Grafana Loki.
---

# Grafana Loki Log Store

The Grafana Loki Log Store is a log store flavor that exports logs to [Grafana Loki](https://grafana.com/oss/loki/) and can retrieve them for display in the ZenML dashboard. It is useful when you already run Loki as part of your observability stack and want ZenML logs available in both ZenML and Grafana.

### When to use it

The Loki Log Store is ideal when:

- You already use Loki/Grafana for centralized logging
- You want server-side log filtering and pagination in ZenML
- You need to correlate ZenML logs with logs from other services
- You prefer operating your own log backend instead of a managed service

### How it works

The Loki Log Store extends the [OTEL Log Store](otel.md):

1. **Log capture**: ZenML captures stdout, stderr, and Python logging output during pipeline execution.

2. **OTEL export**: Logs are converted to OpenTelemetry records and sent to the configured OTLP endpoint.

3. **Loki query**: ZenML fetches logs from Loki using the Loki `query_range` API and LogQL filters.

4. **Cursor pagination**: Results are returned with `before`/`after` cursors so the dashboard can page through logs efficiently.

#### ZenML-specific attributes

Loki stores structured metadata for each log record. In Loki queries, ZenML attributes are normalized with underscores (for example, `zenml.log.id` is available as `zenml_log_id`).

Each log record includes ZenML metadata that can be used for filtering in Loki:

| Attribute | Description |
|---|---|
| `zenml_log_id` | Unique identifier for the log stream |
| `zenml_log_source` | Source of the log (step, pipeline, etc.) |
| `zenml_log_uri` | URI where logs are stored (if applicable) |
| `zenml_log_store_id` | ID of the log store component |
| `zenml_log_store_name` | Name of the log store component |
| `zenml_run_id` | Pipeline run ID |
| `zenml_user_id` | User ID |
| `zenml_user_name` | User name |
| `zenml_project_id` | Project ID |
| `zenml_project_name` | Project name |
| `zenml_stack_id` | Stack ID |
| `zenml_stack_name` | Stack name |
| `zenml_pipeline_id` | Pipeline ID |
| `zenml_pipeline_name` | Pipeline name |
| `zenml_pipeline_run_id` | Pipeline run ID |
| `zenml_pipeline_run_name` | Pipeline run name |
| `zenml_step_run_id` | Step ID (for step-level logs) |
| `zenml_step_run_name` | Step name (for step-level logs) |
| `zenml_workspace_id` | Workspace ID (when connected to a ZenML Pro workspace) |
| `zenml_workspace_name` | Workspace name (when connected to a ZenML Pro workspace) |

### How to deploy it

The Loki Log Store comes built-in with ZenML. You need:

1. A Loki ingestion endpoint (OTLP over HTTP)
2. A Loki query endpoint (`/loki/api/v1/query_range`)
3. Optional credentials (API key or username/password)

### How to use it

#### Basic setup

```shell
zenml log-store register loki_logs \
    --flavor=loki \
    --endpoint=http://localhost:4318/v1/logs \
    --query_range_url=http://localhost:3100/loki/api/v1/query_range

zenml stack register my_stack \
    -a my_artifact_store \
    -o default \
    -ls loki_logs \
    --set
```

#### With API key authentication

```shell
zenml secret create loki_secrets --api_key=<YOUR_LOKI_API_KEY>

zenml log-store register loki_logs \
    --flavor=loki \
    --endpoint=https://loki.example.com/otlp/v1/logs \
    --query_range_url=https://loki.example.com/loki/api/v1/query_range \
    --api_key='{{loki_secrets.api_key}}'
```

#### With basic authentication

```shell
zenml secret create loki_basic_auth \
    --username=<YOUR_USERNAME> \
    --password=<YOUR_PASSWORD>

zenml log-store register loki_logs \
    --flavor=loki \
    --endpoint=https://loki.example.com/otlp/v1/logs \
    --query_range_url=https://loki.example.com/loki/api/v1/query_range \
    --username='{{loki_basic_auth.username}}' \
    --password='{{loki_basic_auth.password}}'
```

### Configuration options

| Parameter                 | Default       | Description                                                     |
|--------------------------|---------------|-----------------------------------------------------------------|
| `endpoint`               | _required_    | OTLP/HTTP endpoint URL for log ingestion                        |
| `query_range_url`        | `None`        | Loki query API URL used for log retrieval                       |
| `api_key`                | `None`        | Bearer token for Loki authentication                            |
| `username`               | `None`        | Username for basic authentication (must be set with `password`) |
| `password`               | `None`        | Password for basic authentication (must be set with `username`) |
| `headers`                | `None`        | Optional custom HTTP headers for ingestion and query requests   |
| `compression`            | `"none"`      | OTLP payload compression: `"none"`, `"gzip"`, or `"deflate"`    |
| `service_name`           | `"zenml"`     | Service name attached to OTEL resource attributes               |
| `service_version`        | ZenML version | Service version attached to OTEL resource attributes            |
| `default_query_size`     | `1000`        | Default number of log entries fetched per request               |
| `max_queue_size`         | `100000`      | Maximum queue size for OTEL batch processor                     |
| `schedule_delay_millis`  | `5000`        | Delay between batch exports (milliseconds)                      |
| `max_export_batch_size`  | `5000`        | Maximum batch size for exports                                  |
| `export_timeout_millis`  | `15000`       | Timeout for each export batch (milliseconds)                    |

{% hint style="info" %}
Use either `api_key` or `username`/`password`, not both.
{% endhint %}

### Viewing logs

#### In ZenML Dashboard

ZenML fetches step and run logs from Loki via the query API and supports filtering and pagination in the dashboard.

#### In Grafana/Loki

You can query logs in Grafana Explore with labels/fields emitted by ZenML, for example filtering by the ZenML log ID attached to each record.

### Troubleshooting

#### Logs are exported but not visible in ZenML

1. Verify `query_range_url` points to the Loki query API endpoint.
2. Confirm authentication headers/credentials are valid for query requests.
3. Check that ingestion `endpoint` and query backend reference the same Loki instance/tenant.

#### Authentication errors

1. Use either API key or basic auth credentials, not both.
2. If using custom `headers`, verify they do not override required auth headers.

#### Empty query results

1. Confirm the configured `service_name` matches what your Loki setup stores.
2. Check time range and filtering constraints.
3. Validate clock synchronization between runners and Loki.

For more information and a full list of configurable attributes, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-log_stores.html#zenml.log_stores.loki.loki_log_store).
