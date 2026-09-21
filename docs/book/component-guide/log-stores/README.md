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

- You want centralized log aggregation and analysis
- You need advanced log querying capabilities beyond what file-based storage provides
- You're running pipelines at scale and need better log management
- You want to integrate with your organization's existing observability infrastructure

### How to use it

By default, if no log store is explicitly configured in your stack, ZenML automatically creates an Artifact Log Store that uses your artifact store for log storage. This means logging works out of the box without any additional configuration.

To use a different log store, choose a [flavor](#log-store-flavors), register it with the required configuration, and add it to your stack:

```shell
# See the flavor's documentation for its configuration options
zenml log-store register <LOG_STORE_NAME> \
    --flavor=<FLAVOR> <CONFIGURATION_OPTIONS>

# Add it to your stack
zenml stack register <STACK_NAME> -a <ARTIFACT_STORE> -o <ORCHESTRATOR> --log_store <LOG_STORE_NAME> --set
```

Once configured, logs are automatically captured during pipeline execution.

### Viewing Logs

Log stores with retrieval support make step logs available in the ZenML dashboard, Python SDK, and REST API. Export-only stores require the backend's own UI or API to read logs.

#### Python SDK

Use the log store that captured the logs:

```python
from zenml.client import Client
from zenml.utils.logging_utils import search_logs_by_source

client = Client()

run = client.get_pipeline_run("<RUN_NAME_OR_ID>")
step_run = run.steps["<STEP_NAME>"]
logs = search_logs_by_source(step_run.log_collection or [], "step")
if logs is None:
    raise ValueError("This step has no execution log stream.")

log_store = client.active_stack.log_store
page = log_store.fetch(logs_model=logs, limit=1000)

for entry in page.items:
    print(f"[{entry.level}] {entry.message}")
```

`fetch()` returns entries in `items`, ordered from oldest to newest. Set `start="oldest"` or `start="newest"` to choose which end of the stream to read, or omit it to use the backend's default. Supported directions and filters depend on the log store.

`limit` controls the number of entries returned. `ZENML_LOGS_MAX_ENTRIES_PER_REQUEST` caps each request at 50,000 by default; a backend may have a lower limit.

For backends with pagination, pass the returned `before` cursor to read older entries or `after` to read newer ones. Only directions supported by the backend's native tokens are available; `None` means there is no continuation in that direction.

For a backend with filtering and pagination towards older entries, filter the first request and use its cursor to continue:

```python
from zenml.models import LogsEntriesFilter

page = log_store.fetch(
    logs_model=logs,
    start="newest",
    filter_=LogsEntriesFilter(level="ERROR", search="ValueError"),
)
while True:
    for entry in page.items:
        print(entry.message)
    if page.before is None:
        break
    page = log_store.fetch(logs_model=logs, before=page.before)
```

Cursors retain the filters, page size, and fixed time bounds, so continuation requests need only the cursor. Search follows the backend's matching rules, which may differ from a literal substring match.

Some backends support filtering but return a single batch without cursors. The artifact log store returns a batch of the oldest entries for client-side filtering and pagination; it does not support server-side filters or `start="newest"`.

Each entry has a UUID `id`. When a backend provides stable IDs, deduplicate entries within a stream by `(id, chunk_index)` to preserve chunks of the same message. See the flavor's documentation for its ID guarantees. Shared log types, including `LogEntry`, are available from `zenml.models`.

#### REST API

`GET /api/v1/logs/{logs_id}/entries` accepts `start`, `limit`, `before`, `after`, `search`, `level`, `since`, and `until` as query parameters. For example:

```http
GET /api/v1/logs/<LOGS_ID>/entries?start=newest&limit=50
GET /api/v1/logs/<LOGS_ID>/entries?before=<CURSOR>
```

Invalid query values return `422`; unsupported parameters and cursors rejected by ZenML return `400`. Backends without log retrieval return `501`. Shared log store errors return `429` for throttling, `503` for unavailability, or `502` for other backend errors. When provided, `Retry-After` specifies the delay in seconds before retrying the original request. Direct SDK calls raise the corresponding `LogStoreError` subclass.

Runner logs return one batch through the workload manager. Apply filtering and pagination in the client; unsupported runner filters or cursors return `400`.

The existing run and step log endpoints continue to return a single list of entries. Use the dedicated entries endpoint for pagination when the backend supports it.

### Log Store Flavors

ZenML provides several log store flavors out of the box:

| Log Store | Flavor | Retrieval |
|-----------|--------|-----------|
| [Artifact Log Store](artifact.md) | `artifact` | One batch for client-side filtering and pagination. Used automatically when no log store is configured. |
| [OpenTelemetry Log Store](otel.md) | `otel` | Export only; read logs through the backend's own UI or API. |
| [Datadog Log Store](datadog.md) | `datadog` | Server-side filtering and native cursor pagination. |
| [Grafana Loki Log Store](loki.md) | `loki` | Server-side filtering with one batch per query. |
| [Elasticsearch Log Store](elasticsearch.md) | `elasticsearch` | Server-side filtering and native cursor pagination. |

All five flavors are built in. You can also [develop a custom log store](custom.md).

If you would like to see the available flavors of log stores, you can use the command:

```shell
zenml log-store flavor list
```

{% hint style="info" %}
If you're interested in understanding the base abstraction and how log stores work internally, check out the [Develop a Custom Log Store](custom.md) page for a detailed explanation of the architecture.
{% endhint %}

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
