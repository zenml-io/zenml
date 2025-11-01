---
description: Exporting logs using OpenTelemetry.
---

# OpenTelemetry Log Store

The OpenTelemetry Log Store allows you to export logs to any OpenTelemetry-compatible backend. It uses the OpenTelemetry SDK to collect and export logs with structured metadata.

### When to use it

Use the OpenTelemetry Log Store when you:

* Want to send logs to any OpenTelemetry-compatible backend
* Need structured logging with rich metadata
* Want to integrate with your existing OpenTelemetry infrastructure
* Need flexibility to change backends without changing your ZenML configuration

### How to deploy it

The OpenTelemetry Log Store requires the OpenTelemetry SDK to be installed:

```bash
pip install opentelemetry-sdk opentelemetry-exporter-otlp
```

### How to use it

Register an OpenTelemetry log store:

```bash
zenml log-store register otel_logs --flavor otel \
    --service_name=zenml-pipelines \
    --endpoint=http://otel-collector:4318
```

Add it to your stack:

```bash
zenml stack update -l otel_logs
```

#### Configuration Options

The OpenTelemetry Log Store supports the following configuration options:

* `service_name`: The name of your service (default: "zenml")
* `service_version`: The version of your service (default: "1.0.0")
* `deployment_environment`: The deployment environment (default: "production")
* `endpoint`: The OTLP endpoint URL (optional)
* `headers`: Custom headers to send with log exports (optional)
* `insecure`: Whether to use an insecure connection (default: False)
* `max_queue_size`: Maximum queue size for batch processing (default: 2048)
* `schedule_delay_millis`: Export interval in milliseconds (default: 1000)
* `max_export_batch_size`: Maximum batch size for exports (default: 512)

#### Resource Attributes

All logs exported through the OpenTelemetry Log Store include the following resource attributes:

* `service.name`: The configured service name
* `service.version`: The configured service version
* `service.instance.id`: A unique instance identifier
* `deployment.environment`: The deployment environment
* `zenml.pipeline_run_id`: The pipeline run UUID
* `zenml.step_id`: The step UUID (if applicable)
* `zenml.source`: The log source ("step" or "orchestrator")

These attributes allow you to filter and aggregate logs by pipeline, step, or environment in your observability platform.

#### Example: Using with an OTLP Collector

```bash
zenml log-store register my_otel_logs --flavor otel \
    --service_name=my-ml-pipelines \
    --deployment_environment=production \
    --endpoint=https://otlp-collector.example.com:4318 \
    --headers='{"Authorization":"Bearer token123"}'
```

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

