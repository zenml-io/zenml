---
description: Storing logs in your artifact store.
---

# Artifact Log Store

The Artifact Log Store is the default [log store](./) flavor that comes built-in with ZenML. It stores logs directly in your artifact store, providing a zero-configuration logging solution that works out of the box.

{% hint style="info" %}
The Artifact Log Store is automatically used when no log store is explicitly configured in your stack. ZenML creates a temporary artifact log store from your artifact store, so logging works immediately without any additional setup.
{% endhint %}

### When would you want to use it?

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

### How to deploy it

The Artifact Log Store comes built-in with ZenML and requires no additional installation. It's automatically available when you install ZenML:

```shell
pip install zenml
```

Since ZenML automatically creates an Artifact Log Store from your artifact store when needed, you typically don't need to explicitly register one. However, if you want to customize its configuration, you can register it explicitly.

### How to use it

#### Automatic usage (recommended)

Simply use your stack without configuring a log store. ZenML will automatically use an Artifact Log Store backed by your artifact store:

```shell
# Just run your pipeline - logging works automatically
python my_pipeline.py
```

#### Explicit registration

If you want to customize the log store configuration or explicitly register it:

```shell
# Register an artifact log store with custom settings
zenml log-store register my_artifact_logs \
    --flavor=artifact \
    --endpoint=<YOUR_ARTIFACT_STORE_PATH>

# Add it to your stack
zenml stack register my_stack \
    -a my_artifact_store \
    -o default \
    -ls my_artifact_logs \
    --set
```

### Configuration options

The Artifact Log Store inherits all configuration options from the [OTEL Log Store](otel.md) since it's built on the same OpenTelemetry foundation:

| Parameter                | Default            | Description                                         |
|--------------------------|--------------------|----------------------------------------------------|
| `service_name`           | `"zenml"`          | Name of the service for telemetry                  |
| `service_version`        | ZenML version      | Version of the service for telemetry               |
| `max_queue_size`         | `2048`             | Maximum queue size for batch log processor         |
| `schedule_delay_millis`  | `5000`             | Delay between batch exports in milliseconds        |
| `max_export_batch_size`  | `512`              | Maximum batch size for exports                     |
| `export_timeout_millis`  | `30000`            | Timeout for each export batch in milliseconds      |
| `endpoint`               | _required_         | Path to the artifact store (set automatically)     |

{% hint style="info" %}
When using the automatic artifact log store (no explicit configuration), these settings use sensible defaults. You only need to customize them if you have specific performance requirements.
{% endhint %}

### Log format

Logs are stored as newline-delimited JSON (NDJSON) files. Each log entry contains:

```json
{
  "message": "Training model with 1000 samples",
  "level": "INFO",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "name": "my_logger",
  "filename": "train.py",
  "lineno": 42,
  "module": "train"
}
```

For large messages (>5KB), logs are automatically chunked with additional metadata:

```json
{
  "message": "First part of large message...",
  "level": "INFO",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "chunk_index": 0,
  "total_chunks": 3,
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Viewing logs

#### Via the Dashboard

Navigate to any pipeline run in the ZenML dashboard. Click on a step to view its logs in the built-in log viewer.

#### Via the CLI

```shell
# List recent pipeline runs
zenml pipeline runs list

# View logs for a specific run (coming soon)
zenml pipeline runs logs <RUN_ID>
```

#### Via Python

```python
from zenml.client import Client

client = Client()
run = client.get_pipeline_run("<RUN_ID>")

# Access step logs
for step_name, step in run.steps.items():
    if step.logs:
        print(f"\n=== Logs for {step_name} ===")
        # Logs are fetched from the artifact store
        log_entries = step.logs.fetch()
        for entry in log_entries:
            print(f"[{entry.level}] {entry.message}")
```

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

3. **Large log volumes**: If you're generating very large log volumes, consider:
   - Adjusting `max_queue_size` and `max_export_batch_size` for better throughput
   - Using a dedicated log store like Datadog for better scalability

4. **Sensitive data**: Be mindful of what you log. Avoid logging sensitive information like credentials or PII.

For more information and a full list of configurable attributes, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-log_stores.html#zenml.log_stores.artifact.artifact_log_store).

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
