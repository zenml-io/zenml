---
description: Storing and retrieving logs from your ML pipelines.
icon: file-lines
---

# Log Stores

The Log Store is a stack component responsible for collecting, storing, and retrieving logs generated during pipeline and step execution. It captures everything from standard logging output to print statements and any messages written to stdout/stderr, making it easy to debug and monitor your ML workflows.

## How Log Capture Works

ZenML's log capture system is designed to be comprehensive and non-intrusive. Here's what happens under the hood:

1. **stdout/stderr wrapping**: ZenML wraps the standard output and error streams to capture all printed messages and any output directed to these streams.

2. **Root logger handler**: A custom handler is added to Python's root logger to capture all log messages from loggers that propagate to the root.

3. **Log routing**: All captured messages are routed through a `LoggingContext` to the active log store in your stack.

This approach ensures that you don't miss any output from your pipeline steps, including:
- Standard Python `logging` messages
- `print()` statements
- Output from third-party libraries
- Messages from subprocesses that write to stdout/stderr

### When to use it

The Log Store is automatically used in every ZenML stack. If you don't explicitly configure a log store, ZenML will use an **Artifact Log Store** by default, which stores logs in your artifact store.

You should consider configuring a dedicated log store when:

- You want to use a centralized logging backend like Datadog for log aggregation and analysis
- You need advanced log querying capabilities beyond what file-based storage provides
- You're running pipelines at scale and need better log management
- You want to integrate with your organization's existing observability infrastructure

### Log Store Flavors

ZenML provides several log store flavors out of the box:

| Log Store                          | Flavor     | Integration | Notes                                                                                           |
|------------------------------------|------------|-------------|------------------------------------------------------------------------------------------------|
| [ArtifactLogStore](artifact.md)    | `artifact` | _built-in_  | Default log store that writes logs to your artifact store. Zero configuration required.        |
| [OtelLogStore](otel.md)            | `otel`     | _built-in_  | Generic OpenTelemetry log store for any OTEL-compatible backend. Does not support log fetching.|
| [DatadogLogStore](datadog.md)      | `datadog`  | _built-in_  | Exports logs to Datadog's log management platform with full fetch support.                     |
| [Custom Implementation](custom.md) | _custom_   |             | Extend the log store abstraction and provide your own implementation.                          |

If you would like to see the available flavors of log stores, you can use the command:

```shell
zenml log-store flavor list
```

### How to use it

By default, if no log store is explicitly configured in your stack, ZenML automatically creates an Artifact Log Store that uses your artifact store for log storage. This means logging works out of the box without any additional configuration.

To use a different log store, you need to register it and add it to your stack:

```shell
# Register a log store (example with Datadog)
zenml log-store register <LOG_STORE_NAME> \
    --flavor=datadog \
    --api_key=<DATADOG_API_KEY> \
    --application_key=<DATADOG_APPLICATION_KEY>

# Add it to your stack
zenml stack register <STACK_NAME> -a <ARTIFACT_STORE> -o <ORCHESTRATOR> -ls <LOG_STORE_NAME> --set
```

Once configured, logs are automatically captured during pipeline execution. You can view logs through:

1. **ZenML Dashboard**: Navigate to a pipeline run and view step logs directly in the UI.
2. **ZenML CLI**: Use `zenml pipeline runs logs <RUN_ID>` to fetch logs.
3. **External platforms**: For log stores like Datadog, you can also view logs directly in the platform's native interface.

### Architecture

The log store system is built on OpenTelemetry (OTEL) standards, providing a robust and extensible foundation for log collection. The architecture consists of three layers:

```
┌─────────────────────────────────────────────────────────┐
│                    Your Pipeline Code                    │
│  (logging, print statements, stdout/stderr output)       │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    LoggingContext                        │
│  (Captures and routes all log output to the log store)   │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      Log Store                           │
│  (BaseLogStore → OtelLogStore → Concrete Implementation) │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend Storage                       │
│  (Artifact Store, Datadog, OTEL-compatible endpoint)     │
└─────────────────────────────────────────────────────────┘
```

**Key components:**

- **BaseLogStore**: The foundational abstraction defining the log store interface (`emit`, `fetch`, `finalize`, `flush`).

- **OtelLogStore**: Extends BaseLogStore with OpenTelemetry infrastructure, including `LoggerProvider`, `BatchLogRecordProcessor`, and configurable exporters.

- **Concrete implementations**: Flavor-specific implementations like `ArtifactLogStore` and `DatadogLogStore` that provide the actual log export and fetch logic.

### Configuration Options

All OTEL-based log stores (which includes most built-in flavors) share common configuration options:

| Parameter                | Default            | Description                                         |
|--------------------------|--------------------|----------------------------------------------------|
| `service_name`           | `"zenml"`          | Name of the service for telemetry                  |
| `service_version`        | ZenML version      | Version of the service for telemetry               |
| `max_queue_size`         | `2048`             | Maximum queue size for batch log processor         |
| `schedule_delay_millis`  | `5000`             | Delay between batch exports in milliseconds        |
| `max_export_batch_size`  | `512`              | Maximum batch size for exports                     |
| `export_timeout_millis`  | `30000`            | Timeout for each export batch in milliseconds      |

These options can be tuned based on your logging volume and latency requirements.

### Viewing Logs

Logs captured by the log store can be accessed in several ways:

#### Via the Dashboard

The ZenML dashboard provides a built-in log viewer for each step in a pipeline run. Simply navigate to the run details page and click on a step to view its logs.

#### Via the Client

```python
from zenml.client import Client

client = Client()

# Get a specific pipeline run
run = client.get_pipeline_run("<RUN_NAME_OR_ID>")

# Access step logs
for step_name, step in run.steps.items():
    logs = step.logs
    if logs:
        print(f"Logs for {step_name}:")
        for entry in logs.fetch():
            print(f"  [{entry.level}] {entry.message}")
```

#### Via External Platforms

For log stores that export to external platforms (like Datadog), you can use those platforms' native interfaces for advanced querying, alerting, and visualization.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
