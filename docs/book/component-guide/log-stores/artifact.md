---
description: Storing logs in your artifact store.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Artifact Log Store

The Artifact Log Store is the default log store flavor that comes built-in with ZenML. It stores logs directly in your artifact store, providing a zero-configuration logging solution that works out of the box.

{% hint style="warning" %}
The Artifact Log Store is ZenML's implicit default. You don't need to register it as a flavor or add it to your stack. When no log store is explicitly configured, ZenML automatically uses an Artifact Log Store to handle logs. This means logging works out of the box with zero configuration.
{% endhint %}

### When to use it

The Artifact Log Store is ideal when:

- You want logging to work without any additional configuration
- You prefer to keep all your pipeline data (artifacts and logs) in one place
- You don't need advanced log querying capabilities
- You're getting started with ZenML and want a simple setup

### How it works

The Artifact Log Store leverages OpenTelemetry's batching infrastructure while using a custom exporter that writes logs to your artifact store. Here's what happens during pipeline execution:

1. **Log capture**: All stdout, stderr, and Python logging output is captured and routed to the log store.

2. **Batching**: Logs are collected in batches using OpenTelemetry's `BatchLogRecordProcessor` for efficient processing.

3. **Export**: The `ArtifactLogExporter` writes batched logs to your artifact store as JSON-formatted log files.

4. **Finalization**: When a step completes, logs are finalized (merged if necessary) to ensure they're ready for retrieval.

#### Handling Different Filesystem Types

The Artifact Log Store handles different artifact store backends intelligently:

- **Mutable filesystems** (local, S3, Azure): Logs are appended to a single file per step.
- **Immutable filesystems** (GCS): Logs are written as timestamped files in a directory, then merged on finalization.

This ensures consistent behavior across all supported artifact store types.

### Environment Variables

The Artifact Log Store uses OpenTelemetry's batch processing under the hood. You can tune the batching behavior using these environment variables:

| Environment Variable                      | Default   | Description                                         |
|------------------------------------------|-----------|-----------------------------------------------------|
| `ZENML_LOGS_OTEL_MAX_QUEUE_SIZE`         | `100000`  | Maximum queue size for batch log processor          |
| `ZENML_LOGS_OTEL_SCHEDULE_DELAY_MILLIS`  | `5000`    | Delay between batch exports in milliseconds         |
| `ZENML_LOGS_OTEL_MAX_EXPORT_BATCH_SIZE`  | `5000`    | Maximum batch size for exports                      |
| `ZENML_LOGS_OTEL_EXPORT_TIMEOUT_MILLIS`  | `15000`   | Timeout for each export batch in milliseconds       |

These defaults are optimized for most use cases. You typically only need to adjust them for high-volume logging scenarios.

### Log format

Logs are stored as newline-delimited JSON (NDJSON) files. Each log entry contains the following fields:

```json
{
  "message": "Training model with 1000 samples",
  "level": "INFO",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "name": "my_logger",
  "filename": "train.py",
  "lineno": 42,
  "module": "train",
  "chunk_index": 0,
  "total_chunks": 1,
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field          | Description                                                                 |
|----------------|-----------------------------------------------------------------------------|
| `message`      | The log message content                                                     |
| `level`        | Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)                             |
| `timestamp`    | When the log was created                                                    |
| `name`         | The name of the logger                                                      |
| `filename`     | The source file that generated the log                                      |
| `lineno`       | The line number in the source file                                          |
| `module`       | The module that generated the log                                           |
| `chunk_index`  | Index of this chunk (0 for non-chunked messages)                           |
| `total_chunks` | Total number of chunks (1 for non-chunked messages)                        |
| `id`           | Unique identifier for the log entry (used to reassemble chunked messages)  |

For large messages (>5KB), logs are automatically split into multiple chunks with sequential `chunk_index` values and a shared `id` for reassembly.

### Storage location

Logs are stored in the `logs` directory within your artifact store:

```
<artifact_store_path>/
└── logs/
    ├── <log_id_1>.log          # For mutable filesystems
    └── <log_id_2>/              # For immutable filesystems (GCS)
        ├── 1705312200.123.log
        ├── 1705312205.456.log
        └── 1705312210.789_merged.log
```

### Best practices

1. **Use the default**: For most use cases, the automatic artifact log store is sufficient. Don't add complexity unless you need it.

2. **Monitor storage**: Logs can accumulate over time. Consider implementing log retention policies for your artifact store.

3. **Large log volumes**: If you're generating very large log volumes, consider using a dedicated log store like Datadog for better scalability and querying.

4. **Sensitive data**: Be mindful of what you log. Avoid logging sensitive information like credentials or PII.

For more information and a full list of configurable attributes, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-log_stores.html#zenml.log_stores.artifact.artifact_log_store).
