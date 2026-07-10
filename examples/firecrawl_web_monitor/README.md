# Firecrawl Web Monitoring with ZenML

This example turns each Firecrawl `monitor.page` webhook into a ZenML pipeline run. Firecrawl monitors and scrapes the page; ZenML preserves the event, diff, analysis, and report as independently versioned artifacts. An LLM interprets the change when an OpenAI key is stored in a ZenML secret and passed via `--llm-secret` (or `LLM_SECRET_NAME` for the webhook receiver), and a configured ZenML alerter can optionally post meaningful changes to Slack.

```text
Firecrawl webhook
       |
       v
raw event -> normalized diff -> LLM analysis -> report -> optional Slack
    v1             v1               v1           v1
    v2             v2               v2           v2
```

The stable artifact names make every run easy to compare in the ZenML dashboard:

- `firecrawl_monitor_event` stores the source webhook.
- `web_page_change` stores the normalized diff and Firecrawl scrape IDs.
- `web_change_analysis` stores the business interpretation.
- `web_monitoring_report` joins the evidence and analysis for downstream use.

## Quick start

This example assumes that a [ZenML stack](https://docs.zenml.io/stacks) is already configured. From this directory, install the small set of example dependencies and run the bundled realistic event:

```bash
uv pip install -e ".[dev]"
zenml init
python run.py
```

Run `zenml init` and all commands from this directory: it sets the ZenML source root, and the pipeline's Docker settings reference the `pyproject.toml` here, so remote image builds pick up the example's dependencies.

If the active stack uses an S3 artifact store, install its client integration in the same environment once:

```bash
zenml integration install s3 --uv
```

No Firecrawl, OpenAI, or Slack credentials are required for that first run. Without an LLM secret, the analysis uses Firecrawl's meaningful-change judgment and clearly labels itself as a fallback. Store the OpenAI key in ZenML to run the same pipeline with an LLM on both local and remote orchestrators:

```bash
zenml secret create firecrawl-monitoring \
  --OPENAI_API_KEY=<your-key> \
  --OPENAI_MODEL=gpt-5-mini
python run.py --llm-secret firecrawl-monitoring
```

Run the example twice, optionally editing `sample_payload.json`, then inspect the artifact versions in the dashboard or from the terminal:

```bash
python history.py
```

## Receive Firecrawl webhooks locally

Start the synchronous FastAPI receiver:

```bash
export FIRECRAWL_WEBHOOK_TOKEN=<shared-secret>
uvicorn webhook_server:app --host 0.0.0.0 --port 8000
```

Expose port 8000 through your preferred development tunnel, then add the public endpoint to a Firecrawl monitor. The authorization header is optional locally but recommended for every public endpoint:

```bash
export FIRECRAWL_API_KEY=<your-firecrawl-key>
python create_firecrawl_monitor.py \
  --target-url https://example.com/pricing \
  --webhook-url https://your-public-host/webhooks/firecrawl \
  --goal "Alert when a competitor changes price or packaging"
```

The script creates an hourly Firecrawl `scrape` monitor. Change the cadence with `--schedule`, for example `--schedule daily`. It uses `FIRECRAWL_WEBHOOK_TOKEN` for the receiver authorization header when that environment variable is set.

The equivalent webhook portion of the monitor request is:

```json
{
  "webhook": {
    "url": "https://your-public-host/webhooks/firecrawl",
    "headers": {
      "Authorization": "Bearer <shared-secret>"
    },
    "metadata": {
      "environment": "trial"
    },
    "events": ["monitor.page", "monitor.check.completed"]
  }
}
```

The receiver ignores `monitor.check.completed` because that event contains only aggregate counts. Each `monitor.page` event starts one pipeline run and carries the page-level diff needed by the analysis.

For production, deploy the receiver behind an authenticated HTTPS endpoint and run ZenML with a [Kubernetes orchestrator](https://docs.zenml.io/stacks/stack-components/orchestrators/kubernetes). The pipeline includes Docker settings sourced from `pyproject.toml`, so the code and artifact contracts do not change when moving from the local orchestrator.

## Optional Slack alerts

Attach a Slack alerter to the active ZenML stack, then enable notifications for CLI runs:

```bash
python run.py --notify-slack
```

For the webhook receiver, set `NOTIFY_SLACK=true` and optionally `LLM_SECRET_NAME=firecrawl-monitoring`. Only reports marked meaningful are sent. If notification is enabled but the active stack has no alerter, the step logs a warning and the run still succeeds.

## Use a real payload directly

Save any Firecrawl `monitor.page` body and pass it to the runner:

```bash
python run.py \
  --payload payload.json \
  --goal "Alert when a competitor changes price or packaging"
```

Firecrawl can emit both unified markdown diffs and structured JSON field diffs. This example preserves both, so a monitor configured for JSON change tracking can compare fields such as prices or availability without parsing prose.

## Tests

```bash
pytest tests/test_analysis.py
```
