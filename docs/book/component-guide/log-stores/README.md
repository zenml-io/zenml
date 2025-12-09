---
description: Storing and retrieving logs from your ML pipelines.
icon: file-lines
---

# Log Stores

The Log Store is a stack component responsible for collecting, storing, and retrieving logs generated during pipeline and step execution. It captures everything from standard logging output to print statements and any messages written to stdout/stderr, making it easy to debug and monitor your ML workflows.

## How Log Capture Works

ZenML wraps the standard output (`stdout`) and standard error (`stderr`) streams during pipeline execution. This means any output from your code—whether it's Python `logging` messages, `print()` statements, or output from third-party libraries—is automatically captured and routed to the active log store in your stack.

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

{% hint style="info" %}
If you're interested in understanding the base abstraction and how log stores work internally, check out the [Develop a Custom Log Store](custom.md) page for a detailed explanation of the architecture.
{% endhint %}

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
2. **External platforms**: For log stores like Datadog, you can also view logs directly in the platform's native interface.
