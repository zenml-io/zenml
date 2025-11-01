---
description: Sending logs directly to Datadog.
---

# Datadog Log Store

The Datadog Log Store sends logs directly to Datadog's logging platform using their HTTP intake API. It extends the OpenTelemetry Log Store and adds Datadog-specific formatting and tagging.

### When to use it

Use the Datadog Log Store when you:

* Already use Datadog for monitoring and observability
* Want to correlate pipeline logs with other Datadog metrics and traces
* Need advanced log analysis and visualization features
* Want to set up alerts based on pipeline log patterns

### How to deploy it

The Datadog Log Store requires the OpenTelemetry SDK to be installed:

```bash
pip install opentelemetry-sdk requests
```

### How to use it

First, obtain your Datadog API key from the Datadog UI (Organization Settings → API Keys).

Register a Datadog log store:

```bash
zenml log-store register datadog_logs --flavor datadog \
    --api_key=<YOUR_DATADOG_API_KEY> \
    --site=datadoghq.com
```

For EU customers, use `datadoghq.eu`:

```bash
zenml log-store register datadog_logs --flavor datadog \
    --api_key=<YOUR_DATADOG_API_KEY> \
    --site=datadoghq.eu
```

Add it to your stack:

```bash
zenml stack update -l datadog_logs
```

#### Configuration Options

The Datadog Log Store supports all OpenTelemetry Log Store options plus:

* `api_key`: Your Datadog API key (required)
* `site`: The Datadog site (default: "datadoghq.com")
  * US: `datadoghq.com`
  * EU: `datadoghq.eu`
  * Other regions: check Datadog documentation
* `additional_tags`: Additional tags to add to all logs (optional)

#### Log Tags

All logs sent to Datadog include the following tags for easy filtering:

* `service:<service_name>`: The service name from your configuration
* `zenml.pipeline_run_id:<uuid>`: The pipeline run identifier
* `zenml.step_id:<uuid>`: The step identifier (if applicable)
* `zenml.source:<source>`: The log source ("step" or "orchestrator")
* `deployment.environment:<env>`: The deployment environment

#### Viewing Logs in Datadog

Once configured, logs will appear in the Datadog Logs Explorer. You can:

1. Go to Datadog → Logs → Search
2. Filter by service: `service:zenml-pipelines`
3. Filter by pipeline: `zenml.pipeline_run_id:<your-run-id>`
4. Filter by step: `zenml.step_id:<your-step-id>`

#### Example: Production Setup

```bash
zenml log-store register prod_datadog_logs --flavor datadog \
    --api_key=$DATADOG_API_KEY \
    --site=datadoghq.com \
    --service_name=ml-pipelines \
    --deployment_environment=production \
    --additional_tags='{"team":"ml-platform","project":"recommendation-system"}'
```

#### Setting Up Alerts

In Datadog, you can create log-based alerts:

1. Go to Datadog → Logs → Configuration → Log Alerts
2. Create a new monitor
3. Set the query to filter your pipeline logs (e.g., `service:zenml-pipelines @zenml.pipeline_run_id:*`)
4. Define alert conditions (e.g., error rate threshold)
5. Configure notifications

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>

