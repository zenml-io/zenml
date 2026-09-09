---
icon: plug
---

# Python client

[Kitaru](https://docs.zenml.io/kitaru) is ZenML's sibling project for recording, replaying, and improving AI agents. The runs that happen in production become sessions you can replay against your real code. `KitaruAPIClient` is the async Python interface to a Kitaru server.

This page groups the client into thematic areas. For the complete, auto-generated API (every method and signature), see the [full Kitaru SDK reference](https://sdkdocs.kitaru.ai/reference/python/client/).

```python
from kitaru.client import KitaruAPIClient

async with KitaruAPIClient() as client:
    server = await client.info.get()
```

The client resolves its server URL from `KITARU_API_URL` or the server selected by `kitaru login`. It resolves credentials from the worker-provided `KITARU_API_TOKEN`, `KITARU_API_KEY`, or stored login credentials. If no server URL is configured, client creation fails instead of guessing a destination.

The client exposes its functionality through resource namespaces accessed as attributes.

## Sessions

`client.sessions` reads and writes the recordings:

* `list` / `iter` / `get` - find sessions, with filters for agent, tag, origin, and time
* `get_with_nodes` / `list_nodes` / `iter_nodes` - read the recorded model and tool calls, with payloads
* `create` / `ingest_nodes` - use the raw recording API that adapters build on
* `merge_evaluations` - attach externally produced evaluation results to a session
* `update` / `delete` - maintain recorded or imported sessions

## Replays and evaluations

* `client.replays` - create and inspect single-session replays: baseline session, optional override, tool policy, and evaluators
* `client.evaluations` - batch-evaluate stored sessions and read evaluation rows back

## Cohorts and experiments

* `client.cohorts` / `client.cohort_versions` - freeze immutable populations of sessions
* `client.experiments` - name a change and start it against a cohort version
* `client.experiment_runs` - inspect a run, its child jobs, and its cancellation state

## Registry

* `client.agents` / `client.agent_versions` - the agents sessions belong to, and the run commands replay executes
* `client.evaluators` / `client.importers` - versioned plugins registered from a script or package
* `client.imports` - import Langfuse, LangSmith, Braintrust, Logfire, or Kitaru JSONL traces as sessions

## Review

* `client.investigations` / `client.annotations` - structure human review as questions, evidence-linked answers, and session verdicts

## Execution and operations

* `client.session_runs` - submit a registered agent version as a job
* `client.workers` / `client.jobs` / `client.tasks` - register workers and inspect, cancel, or recover queued work
* `client.tags` - group sessions, versions, cohorts, and experiments
* `client.blobs` / `client.secrets` - store plugin source and runtime credentials

## Authentication

* `client.auth` / `client.devices` - authenticate interactive clients
* `client.api_keys` / `client.service_accounts` - issue and rotate process credentials
* `client.accounts` / `client.users` - inspect accounts and their users

***

For complete signatures and the full method list, see the [Python SDK reference](https://sdkdocs.kitaru.ai/reference/python/client/). For the command-line equivalents, see the [Kitaru CLI reference](https://sdkdocs.kitaru.ai/cli/). For the TypeScript client, see [How to use the SDK](https://docs.zenml.io/kitaru/get-help/sdks).
