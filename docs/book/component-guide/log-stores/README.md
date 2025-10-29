---
description: Collecting and storing logs from your pipeline runs.
icon: file-lines
---

# Log Stores

The Log Store is a stack component that handles the collection, storage, and retrieval of logs generated during pipeline and step execution. It provides a centralized way to manage logs across different backends.

ZenML automatically captures logs from your pipeline runs, including stdout, stderr, and any logging output from your steps. The Log Store determines where these logs are stored and how they can be retrieved later for debugging and monitoring.

{% hint style="info" %}
By default, if no Log Store is configured in your stack, ZenML will automatically use the Artifact Store as a fallback location for storing logs. This ensures backward compatibility and that logs are always captured without requiring additional configuration.
{% endhint %}

### When to use it

The Log Store is an optional component in the ZenML stack. While ZenML provides a default fallback mechanism (using the Artifact Store), you may want to configure a dedicated Log Store when you need:

* **Centralized logging infrastructure**: Send logs to your existing logging platform (e.g., Datadog, Elasticsearch, Splunk)
* **Real-time log streaming**: View logs as they are generated during pipeline execution
* **Advanced log analysis**: Use specialized logging platforms for searching, filtering, and analyzing logs
* **Compliance requirements**: Store logs in specific systems for regulatory or audit purposes

#### Log Store Flavors

Out of the box, ZenML provides several Log Store implementations:

| Log Store          | Flavor     | Integration | Notes                                                                         |
| ------------------ | ---------- | ----------- | ----------------------------------------------------------------------------- |
| [OpenTelemetry](otel.md) | `otel`     | _built-in_  | Generic OpenTelemetry-based log store that can export to various backends    |
| [Datadog](datadog.md)    | `datadog`  | _built-in_  | Sends logs directly to Datadog's logging platform                            |
| [Custom Implementation](custom.md) | _custom_   |             | Extend the Log Store abstraction and provide your own implementation         |

If you would like to see the available flavors of Log Stores, you can use the command:

```shell
zenml log-store flavor list
```

### How to use it

The Log Store works automatically once configured in your stack. You don't need to make any changes to your pipeline code. All logging output, print statements, and errors are automatically captured and sent to the configured Log Store.

#### Basic Setup

To register and configure a Log Store:

```shell
# Register a log store
zenml log-store register my_datadog_logs --flavor datadog \
    --api_key=<YOUR_API_KEY> \
    --site=datadoghq.com

# Add it to your stack
zenml stack update -l my_datadog_logs
```

Once configured, all subsequent pipeline runs will send their logs to the configured Log Store.

#### Viewing Logs

Logs can be viewed through:

1. **ZenML Dashboard**: View logs directly in the pipeline run UI
2. **CLI**: Use `zenml logs` commands to fetch and display logs
3. **External Platform**: Access logs directly in your logging platform (e.g., Datadog UI)

#### Log Metadata

All logs captured by ZenML include important metadata:

* `pipeline_run_id`: The unique identifier of the pipeline run
* `step_id`: The unique identifier of the step (if applicable)
* `source`: Where the logs originated from (e.g., "step", "orchestrator")

This metadata allows you to filter and query logs effectively in your logging platform.

#### Fallback Behavior

If no Log Store is configured in your stack, ZenML will:

1. Automatically use the Artifact Store as the storage backend
2. Save logs as files in the artifact store
3. Make logs accessible through the same APIs and UI

This ensures that logs are always captured and retrievable, even without explicit Log Store configuration.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

