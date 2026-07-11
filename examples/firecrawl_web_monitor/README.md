# Firecrawl Web Monitoring with ZenML

This example turns each Firecrawl `monitor.page` event into a ZenML pipeline run. Firecrawl monitors and scrapes the page; ZenML preserves the event, diff, analysis, and report as independently versioned artifacts. An LLM interprets the change when an OpenAI key is stored in a ZenML secret and passed via `--llm-secret`, and a configured ZenML alerter can optionally post meaningful changes to Slack.

```text
Firecrawl monitor.page event (pulled via API or delivered by webhook)
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
uv pip install -e .
zenml init
python run.py
```

Run `zenml init` and all commands from this directory: it sets the ZenML source root, and the pipeline's Docker settings reference the `pyproject.toml` here, so remote image builds pick up the example's dependencies. Note that `zenml init` also scopes the active stack to this directory and resets it to `default`, so select your stack afterwards:

```bash
zenml stack set <your-stack-name>
```

If that stack uses an S3 artifact store, install its client integration in the same environment once, before running the pipeline:

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

## Monitor a real page

Create an hourly Firecrawl `scrape` monitor for the page you care about — no webhook infrastructure needed:

```bash
export FIRECRAWL_API_KEY=<your-firecrawl-key>
python create_firecrawl_monitor.py \
  --target-url https://news.ycombinator.com/newest \
  --goal "Alert when new AI or developer-tooling stories are posted" \
  --schedule "every 5 minutes"
```

A fast-changing page with a short cadence produces meaningful diffs within minutes — ideal for a first demo; dial it back with `--schedule hourly` or `--schedule daily` for real monitoring. Once at least one check has completed, pull it straight from the Firecrawl API and analyze it — one pipeline run per monitored page:

```bash
python run.py --monitor-id <monitor-id>
```

This fetches the latest completed check (or a specific one with `--check-id`) and feeds each page result through the same pipeline as the bundled sample, so the artifact history mixes local experiments and real checks seamlessly.

## Production: trigger a pipeline snapshot

For an event-driven setup, ZenML supports this natively — no custom receiver required. Publish the pipeline as a [snapshot](https://docs.zenml.io/concepts/snapshots) on a remote stack with a remote orchestrator, a container registry, and a remote artifact store (for example a [Kubernetes orchestrator](https://docs.zenml.io/stacks/stack-components/orchestrators/kubernetes)); the pipeline's Docker settings are already sourced from this `pyproject.toml`, so the code and artifact contracts do not change:

```bash
zenml stack set <your-remote-stack>
zenml pipeline snapshot create pipelines.monitoring.firecrawl_web_monitor_pipeline \
  --name firecrawl-web-monitor \
  --config configs/snapshot.yaml
```

`configs/snapshot.yaml` provides the default parameters baked into the snapshot (the bundled sample payload); every trigger can override them. Trigger a run from Python:

```python
from zenml.client import Client

Client().trigger_pipeline(
    snapshot_name_or_id="firecrawl-web-monitor",
    run_configuration={"parameters": {"payload": <monitor-page-event>}},
)
```

Snapshots can also be [triggered from external systems](https://docs.zenml.io/user-guides/tutorial/trigger-pipelines-from-external-systems) with a single authenticated REST call, which is where Firecrawl's webhook plugs in.

Tip for Apple Silicon: images build for `linux/amd64` under emulation, where `uv` can crash. If the build fails with exit code 139, override the installer with `settings: {docker: {python_package_installer: pip}}` in the snapshot config.

## Optional Slack alerts

Attach a Slack alerter to the active ZenML stack, then enable notifications for CLI runs:

```bash
python run.py --notify-slack
```

Only reports marked meaningful are sent. If notification is enabled but the active stack has no alerter, the step logs a warning and the run still succeeds.

## Use a real payload directly

Save any Firecrawl `monitor.page` body and pass it to the runner:

```bash
python run.py \
  --payload payload.json \
  --goal "Alert when a competitor changes price or packaging"
```

Firecrawl can emit both unified markdown diffs and structured JSON field diffs. This example preserves both, so a monitor configured for JSON change tracking can compare fields such as prices or availability without parsing prose.