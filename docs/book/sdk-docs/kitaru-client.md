---
icon: plug
---

# Client

[Kitaru](https://docs.zenml.io/kitaru) is ZenML's durable execution layer for AI agents. `KitaruClient` is the programmatic interface to a Kitaru server — inspect and control flow executions, browse artifacts, invoke deployments, and manage authentication from Python.

This page groups the client into thematic areas. For the complete, auto-generated API (every method and signature), see the [full Kitaru SDK reference](https://sdkdocs.kitaru.ai/reference/python/client/).

```python
import kitaru

client = kitaru.KitaruClient()
```

The client exposes its functionality through sub-APIs accessed as attributes: `client.executions`, `client.artifacts`, `client.deployments`, and `client.auth`.

## Executions

Inspect and control flow executions via `client.executions`:

* `get` — fetch a single execution by ID
* `list` — list executions
* `latest` — the most recent execution
* `logs` — retrieve runtime logs for an execution
* `input` — provide input to an execution waiting on `kitaru.wait()`
* `retry` — retry a failed execution
* `resume` — resume a waiting execution after input lands
* `cancel` — cancel a running execution
* `replay` — replay from a checkpoint, optionally overriding cached outputs

## Artifacts

Browse and read checkpoint outputs and saved artifacts via `client.artifacts`.

## Deployments

Invoke and inspect deployed flows via `client.deployments`:

* `invoke` — start a new execution from a deployed flow (by name + tag/version)
* `list` / `get` — inspect available deployment routes

## Authentication

Manage service accounts and API keys for server access via `client.auth`.

***

For complete signatures and the full method list, see the [Kitaru SDK reference](https://sdkdocs.kitaru.ai/reference/python/client/). For the command-line equivalents, see the [Kitaru CLI reference](https://sdkdocs.kitaru.ai/cli/).
