---
description: Exporting logs to any OpenTelemetry-compatible backend.
---

# OpenTelemetry Log Store

The OpenTelemetry (OTEL) Log Store is a log store flavor that exports logs to any OpenTelemetry-compatible backend using the OTLP/HTTP protocol with JSON encoding. Built on the [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/), it provides maximum flexibility for integrating with your existing observability infrastructure.

{% hint style="warning" %}
The OTEL Log Store is a **write-only** log store. It can export logs to an OTEL-compatible endpoint, but it cannot fetch logs back for display in the ZenML dashboard. If you need log retrieval capabilities, you can extend this log store and implement the `fetch()` method for your backend. See [Develop a Custom Log Store](custom.md) for details on how to do this.
{% endhint %}

### When to use it

The OTEL Log Store is ideal when:

- You have an existing OpenTelemetry-compatible observability platform (e.g., Jaeger, Grafana Tempo, Honeycomb, Lightstep, Dash0)
- You want to consolidate ML pipeline logs with your application logs
- You need to export logs to a custom backend that supports OTLP
- You're building a custom log ingestion pipeline

### How it works

The OTEL Log Store implements the OpenTelemetry logging specification:

1. **Log capture**: All stdout, stderr, and Python logging output is captured during pipeline execution.

2. **OTEL conversion**: Log records are converted to the OpenTelemetry log format with ZenML-specific attributes.

3. **Batching**: Logs are batched using OpenTelemetry's `BatchLogRecordProcessor` for efficient export.

4. **Export**: Batched logs are sent to your configured endpoint using OTLP/HTTP with JSON encoding and optionally, using data compression.

#### ZenML-specific attributes

Each log record includes ZenML metadata as OTEL attributes:

| Attribute              | Description                                    |
|-----------------------|------------------------------------------------|
| `zenml.log.id`        | Unique identifier for the log stream           |
| `zenml.log.source`    | Source of the log (step, pipeline, etc.)       |
| `zenml.log_store.id`  | ID of the log store component                  |
| `zenml.log_store.name`| Name of the log store component                |
| `zenml.run.id`        | Pipeline run ID                                |
| `zenml.step.name`     | Step name (for step-level logs)                |

These attributes enable powerful filtering and querying in your observability platform.

### How to use it

You need to have an OpenTelemetry-compatible endpoint ready to receive logs. This could be:

- A self-hosted OTEL Collector
- A managed observability platform (Grafana Cloud, Honeycomb, etc.)
- Any service that accepts OTLP/HTTP with JSON encoding

Register the OTEL log store with your endpoint configuration:

```shell
# Register an OTEL log store
zenml log-store register my_otel_logs \
    --flavor=otel \
    --endpoint=https://otel-collector.example.com/v1/logs

# Add it to your stack
zenml stack register my_stack \
    -a my_artifact_store \
    -o default \
    -ls my_otel_logs \
    --set
```

#### With authentication headers

Most OTEL backends require authentication. You can pass headers using a ZenML secret:

```shell
# Create a secret with your API key
zenml secret create otel_auth \
    --api_key=<YOUR_API_KEY>

# Register the log store with the header
zenml log-store register my_otel_logs \
    --flavor=otel \
    --endpoint=https://otel-collector.example.com/v1/logs \
    --headers='{"Authorization": "Bearer {{otel_auth.api_key}}"}'
```

#### With TLS certificates

For endpoints requiring client certificates:

```shell
zenml log-store register my_otel_logs \
    --flavor=otel \
    --endpoint=https://secure-collector.example.com/v1/logs \
    --certificate_file=/path/to/ca.crt \
    --client_certificate_file=/path/to/client.crt \
    --client_key_file=/path/to/client.key
```

### Configuration options

| Parameter                  | Default            | Description                                         |
|----------------------------|--------------------|----------------------------------------------------|
| `endpoint`                 | _required_         | OTLP/HTTP endpoint URL for log ingestion           |
| `headers`                  | `None`             | Optional headers for authentication                |
| `certificate_file`         | `None`             | Path to CA certificate file for TLS verification   |
| `client_certificate_file`  | `None`             | Path to client certificate file for mTLS           |
| `client_key_file`          | `None`             | Path to client key file for mTLS                   |
| `compression`              | `"none"`           | Compression type: `"none"`, `"gzip"`, or `"deflate"`|
| `service_name`             | `"zenml"`          | Service name in OTEL resource attributes           |
| `service_version`          | ZenML version      | Service version in OTEL resource attributes        |
| `max_queue_size`           | `100000`           | Maximum queue size for batch processor             |
| `schedule_delay_millis`    | `5000`             | Delay between batch exports (milliseconds)         |
| `max_export_batch_size`    | `5000`             | Maximum batch size for exports                     |
| `export_timeout_millis`    | `15000`            | Timeout for each export batch (milliseconds)       |

### Retry behavior

The OTEL Log Store includes built-in retry logic for transient failures:

- **Retried status codes**: 408, 429, 500, 502, 503, 504
- **Connection retries**: 5 attempts with exponential backoff
- **Read retries**: 5 attempts
- **Backoff factor**: 0.5 seconds

This ensures reliable log delivery even in unstable network conditions.

### Limitations

1. **No log fetching**: The OTEL Log Store cannot retrieve logs for display in the ZenML dashboard. You must use your observability platform's native interface to view logs.

2. **Dashboard integration**: Since logs cannot be fetched, the ZenML dashboard will show "Logs not available" for steps using this log store.

3. **Endpoint compatibility**: Your endpoint must support OTLP/HTTP with JSON encoding. Protobuf-only endpoints are not supported.

### Best practices

1. **Use compression**: Enable `gzip` compression for high-volume logging to reduce network bandwidth.

2. **Tune batch settings**: Adjust `max_queue_size` and `max_export_batch_size` based on your log volume:
   - High volume: Increase both values
   - Low latency needs: Decrease `schedule_delay_millis`

3. **Monitor the endpoint**: Ensure your OTEL collector or backend can handle the log volume from your pipelines.

4. **Use secrets for credentials**: Always store API keys and tokens in ZenML secrets, not in plain text.

For more information and a full list of configurable attributes, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-log_stores.html#zenml.log_stores.otel.otel_log_store).
