---
description: Storing logs in your artifact store.
---

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

#### Cloud IO acceleration

For cloud-backed artifact stores, ZenML can use optional provider-native helpers behind the same public APIs. The log format, artifact locations, and SDK methods do not change; the difference is that ZenML can ask the cloud provider to do fewer, larger operations instead of many small file-like operations.

- **GCS**: Immutable log fragments can be finalized with GCS compose operations. This avoids downloading every fragment into the ZenML process and re-uploading the merged log. GCS only composes up to 32 source objects at a time, so ZenML uses temporary intermediate compose objects for larger fragment sets and then cleans them up. If compose or cleanup is not available, ZenML falls back to the portable artifact-store path. The stored logs are still NDJSON and existing `.log` files or directory-style log URIs remain readable.
- **S3**: ZenML can use native object listing, bulk deletion, ranged reads, and boto3 transfer helpers. This is especially useful for many-file artifact downloads and cleanup of log objects. On versioned buckets, cleanup may need to account for object versions; if the provider-specific path cannot handle a case safely, ZenML falls back to existing file-like behavior.
- **Azure Blob Storage**: ZenML can use append blobs for log writes, blob batch deletion for cleanup, ranged reads, and native download helpers. Append blobs have provider limits on append block size and block count, so ZenML falls back to the existing `adlfs` path when append blobs are not suitable or not supported for the target URI.

Raw artifact downloads through `ArtifactVersionResponse.download_files()` still create a local ZIP file with the same public API and ZIP entry names as before. When supported by the artifact store, ZenML lists objects once and downloads them to a temporary local directory with provider-native transfer helpers before building the ZIP. Stores without these helpers keep the existing streaming behavior. This does not add provider-side ZIP creation, and it does not change non-recursive artifact download behavior.

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

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
