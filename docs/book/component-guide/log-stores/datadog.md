---
description: Exporting logs to Datadog's log management platform.
---

# Datadog Log Store

The Datadog Log Store is a log store flavor that exports logs to [Datadog's log management platform](https://www.datadoghq.com/product/log-management/). It provides full integration with Datadog, including both log export and retrieval, enabling you to view pipeline logs directly in the ZenML dashboard.

### When would you want to use it?

The Datadog Log Store is ideal when:

- You're already using Datadog for application monitoring and want to consolidate ML pipeline logs
- You need advanced log querying, filtering, and alerting capabilities
- You want to correlate ML pipeline logs with other application metrics and traces
- You need long-term log retention with Datadog's archiving features
- You want to view logs both in the ZenML dashboard and Datadog's native interface

### How it works

The Datadog Log Store extends the [OTEL Log Store](otel.md) with Datadog-specific functionality:

1. **Log capture**: All stdout, stderr, and Python logging output is captured during pipeline execution.

2. **OTEL conversion**: Log records are converted to the OpenTelemetry format with ZenML-specific attributes.

3. **Datadog export**: A custom `DatadogLogExporter` sends logs to Datadog's OTLP intake endpoint with proper attribute mapping for Datadog's log structure.

4. **Log retrieval**: The log store uses Datadog's Logs Search API to fetch logs for display in the ZenML dashboard.

#### ZenML-specific attributes

Each log record includes ZenML metadata that can be used for filtering in Datadog:

| Attribute              | Description                                    |
|-----------------------|------------------------------------------------|
| `@zenml.log.id`       | Unique identifier for the log stream           |
| `@zenml.log.source`   | Source of the log (step, pipeline, etc.)       |
| `@zenml.log.uri`      | URI where logs are stored (if applicable)      |
| `@zenml.log_store.id` | ID of the log store component                  |
| `@zenml.log_store.name`| Name of the log store component               |
| `@zenml.run.id`       | Pipeline run ID                                |
| `@zenml.step.name`    | Step name (for step-level logs)                |

### How to deploy it

The Datadog Log Store comes built-in with ZenML. You need:

1. A Datadog account with log management enabled
2. A Datadog API key (for log ingestion)
3. A Datadog Application key (for log retrieval)

#### Getting your keys

1. **API Key**: Navigate to **Organization Settings** → **API Keys** in Datadog
2. **Application Key**: Navigate to **Organization Settings** → **Application Keys** in Datadog

{% hint style="info" %}
Both the API key and Application key are **required** to register a Datadog log store. The API key is used for log ingestion, while the Application key is used for log retrieval (displaying logs in the ZenML dashboard).
{% endhint %}

### How to use it

#### Basic setup

```shell
# Create a secret with your Datadog keys
zenml secret create datadog_keys \
    --api_key=<YOUR_DATADOG_API_KEY> \
    --application_key=<YOUR_DATADOG_APPLICATION_KEY>

# Register the Datadog log store
zenml log-store register datadog_logs \
    --flavor=datadog \
    --api_key='{{datadog_keys.api_key}}' \
    --application_key='{{datadog_keys.application_key}}'

# Add it to your stack
zenml stack register my_stack \
    -a my_artifact_store \
    -o default \
    -ls datadog_logs \
    --set
```

#### With a different Datadog site

Datadog has multiple regional sites. Specify your site if you're not using the default (`datadoghq.com`):

```shell
zenml log-store register datadog_logs \
    --flavor=datadog \
    --api_key='{{datadog_keys.api_key}}' \
    --application_key='{{datadog_keys.application_key}}' \
    --site=datadoghq.eu  # For EU region
```

Available sites:
- `datadoghq.com` (US1 - default)
- `us3.datadoghq.com` (US3)
- `us5.datadoghq.com` (US5)
- `datadoghq.eu` (EU)
- `ap1.datadoghq.com` (AP1)

#### With a custom service name

```shell
zenml log-store register datadog_logs \
    --flavor=datadog \
    --api_key='{{datadog_keys.api_key}}' \
    --application_key='{{datadog_keys.application_key}}' \
    --service_name=my-ml-pipelines
```

### Configuration options

| Parameter                | Default            | Description                                         |
|--------------------------|--------------------|----------------------------------------------------|
| `api_key`                | _required_         | Datadog API key for log ingestion                  |
| `application_key`        | _required_         | Datadog Application key for log retrieval          |
| `site`                   | `"datadoghq.com"`  | Datadog site (e.g., `datadoghq.eu`)                |
| `service_name`           | `"zenml"`          | Service name shown in Datadog logs                 |
| `service_version`        | ZenML version      | Service version shown in Datadog logs              |
| `max_export_batch_size`  | `500`              | Maximum batch size (Datadog limit: 1000)           |
| `max_queue_size`         | `100000`           | Maximum queue size for batch processor             |
| `schedule_delay_millis`  | `5000`             | Delay between batch exports (milliseconds)         |
| `export_timeout_millis`  | `15000`            | Timeout for each export batch (milliseconds)       |

{% hint style="warning" %}
Datadog has a maximum batch size limit of 1000 logs per request. The `max_export_batch_size` is capped at this value.
{% endhint %}

### Viewing logs

#### In ZenML Dashboard

Logs are automatically fetched from Datadog when viewing step details in the ZenML dashboard. The dashboard uses Datadog's Logs Search API to retrieve logs filtered by the step's log ID.

#### In Datadog

Navigate to **Logs** in your Datadog dashboard and use these filters:

```
service:zenml @zenml.run.id:<YOUR_RUN_ID>
```

Or filter by specific step:

```
service:zenml @zenml.step.name:my_training_step
```

### Troubleshooting

#### Logs not appearing in Datadog

1. Verify your API key is correct
2. Check that you're looking at the correct Datadog site
3. Ensure the service name filter matches your configuration
4. Allow a few minutes for logs to be indexed

#### Logs not appearing in ZenML Dashboard

1. Verify your Application key is correct
2. Ensure the Application key has the `logs_read` scope
3. Check that the Datadog site configuration matches

#### Rate limiting

If you're hitting Datadog's rate limits:
- Increase `schedule_delay_millis` to reduce export frequency
- Decrease `max_export_batch_size` for more frequent, smaller batches
- Consider log sampling for high-volume pipelines

For more information and a full list of configurable attributes, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-log_stores.html#zenml.log_stores.datadog.datadog_log_store).
