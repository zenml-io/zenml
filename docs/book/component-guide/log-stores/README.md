---
description: Storing and retrieving logs from your ML pipelines.
icon: file-lines
---

# Log Stores

The log store is a stack component responsible for collecting, storing, and retrieving logs generated during pipeline and step execution. It captures everything from standard logging output to print statements and any messages written to stdout/stderr, making it easy to debug and monitor your ML workflows.

### How it works

ZenML's log capture system is designed to be comprehensive and non-intrusive. Here's what happens under the hood:

1. **stdout/stderr wrapping**: ZenML wraps the standard output and error streams to capture all printed messages and any output directed to these streams.

2. **Root logger handler**: A custom handler is added to Python's root logger to capture all log messages with proper metadata from loggers that propagate to the root.

3. **Log routing**: All captured messages are routed through a `LoggingContext` to the active log store in your stack.

This approach ensures that you don't miss any output from your pipeline steps, including:
- Standard Python `logging` messages
- `print()` statements
- Output from third-party libraries
- Messages from subprocesses that write to stdout/stderr

### When to use it

The Log Store is automatically used in every ZenML stack. If you don't explicitly configure a log store, ZenML will use an [**Artifact Log Store**](artifact.md) by default, which stores logs in your artifact store.

You should consider configuring a dedicated log store when:

- You want to use a centralized logging backend like Datadog, Jaeger, Grafana Tempo, Honeycomb, Lightstep or Dash0 for log aggregation and analysis
- You need advanced log querying capabilities beyond what file-based storage provides
- You're running pipelines at scale and need better log management
- You want to integrate with your organization's existing observability infrastructure

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

Once configured, logs are automatically captured during pipeline execution.

### Viewing Logs

You can view logs through several methods:

1. **ZenML Dashboard**: Navigate to a pipeline run and view step logs directly in the UI.

2. **Programmatically**: You can fetch logs directly using the log store:

```python
from zenml.client import Client
from zenml.utils.logging_utils import search_logs_by_source

client = Client()

# Get the run you want logs for. A run collects several log streams, one per
# source: "orchestrator" for the run itself, "step" for each of its steps.
run = client.get_pipeline_run("<RUN_NAME_OR_ID>")
logs = search_logs_by_source(run.log_collection, "orchestrator")

# Note: The log store must match the one that captured the logs
log_store = client.active_stack.log_store
page = log_store.fetch(logs_model=logs, limit=1000)

for entry in page.items:
    print(f"[{entry.level}] {entry.message}")
```

`start` picks which end of the stream a read begins at. Omit it to let the log store pick (typically the oldest end). It is not a sort order: entries within a page always run from oldest to newest either way. 

A page may carry `before`, `after`, both, or neither. Pass `before` back in to walk towards older entries, and `after` to walk towards newer ones. A slot that comes back as `None` means this store cannot go that way from this page.

```python
# Start at the end of a stream and walk back through its history.
page = log_store.fetch(logs_model=logs, start="newest")
while page.before:
    page = log_store.fetch(
        logs_model=logs,
        before=page.before,
    )
```

Filters are pushed down into the backend's own query, so they cost nothing to apply:

```python
from zenml.models import LogsEntriesFilter

page = log_store.fetch(
    logs_model=logs,
    filter_=LogsEntriesFilter(level="ERROR", search="ValueError"),
)
```

3. **Through the REST API**: `GET /api/v1/logs/{logs_id}/entries` serves the same pages over HTTP, taking `start`, `limit`, `before`, `after`, and the `search`, `level`, `since` and `until` filters as query parameters. A request a log store cannot serve comes back as `400`. This is what the dashboard uses.

4. **External platforms**: For log stores like Datadog, you can also view logs directly in the platform's native interface.

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

{% hint style="info" %}
If you're interested in understanding the base abstraction and how log stores work internally, check out the [Develop a Custom Log Store](custom.md) page for a detailed explanation of the architecture.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
