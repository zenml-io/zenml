---
icon: plug
---

# Client

[Kitaru](https://docs.zenml.io/kitaru) is ZenML's sibling project for recording, replaying, and improving AI agents — the runs that happen in production become sessions you can replay against your real code. `KitaruAPIClient` is the async programmatic interface to a Kitaru server.

This page groups the client into thematic areas. For the complete, auto-generated API (every method and signature), see the [full Kitaru SDK reference](https://sdkdocs.kitaru.ai/reference/python/client/).

```python
from kitaru.client import KitaruAPIClient

client = KitaruAPIClient()   # server and credential resolve from the environment
```

The client exposes its functionality through sub-APIs accessed as attributes.

## Sessions

`client.sessions` reads and writes the recordings:

* `list` / `iter` / `get` — find sessions, with filters for agent, tag, origin, and time
* `list_nodes` — the recorded model and tool calls, with payloads
* `create` / `ingest_nodes` — the raw recording API adapters are built on
* `merge_evaluations` — write evaluations (including human verdicts) onto a session

## Replays and evaluations

* `client.replays` — create and inspect single-session replays: baseline session, optional override, tool policy, evaluators
* `client.evaluations` — batch-evaluate stored sessions and read evaluation rows back

## Cohorts and experiments

* `client.cohorts` / `client.cohort_versions` — freeze immutable populations of sessions
* `client.experiments` — name a change (override, tool policy, evaluators) and `start_run` it against a cohort version

## Registry

* `client.agents` / `client.agent_versions` — the agents sessions belong to, and the run commands replay executes
* `client.evaluators` / `client.importers` — versioned plugins, registered from a script or package
* `client.imports` — bring Langfuse exports in as sessions

## Review

* `client.investigations` / `client.annotations` — structured human review: questions over a set of sessions, answers pinned to exact trace locations

## Operations

* `client.workers` / `client.jobs` — the execution fleet and the work it claims
* `client.api_keys` / `client.accounts` — authentication for processes and people

***

For complete signatures and the full method list, see the [Kitaru SDK reference](https://sdkdocs.kitaru.ai/reference/python/client/). For the command-line equivalents, see the [Kitaru CLI reference](https://sdkdocs.kitaru.ai/cli/).
