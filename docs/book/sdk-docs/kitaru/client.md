---
icon: plug
---

# Client

[Kitaru](https://docs.zenml.io/kitaru) is ZenML's sibling project for running, replaying, and improving AI agents. `KitaruClient` is the programmatic interface to a Kitaru server — inspect and control flow executions, browse artifacts, invoke deployments, and manage authentication from Python.

This page groups the client into thematic areas. For the complete, auto-generated API (every method and signature), see the [full Kitaru SDK reference](https://sdkdocs.kitaru.ai/reference/python/client/).

```python
import kitaru

client = kitaru.KitaruClient()
```

The client exposes its functionality through sub-APIs accessed as attributes.

## Executions

[`client.executions`](https://sdkdocs.kitaru.ai/reference/python/client/) inspects and controls flow executions:

* [`get`](https://sdkdocs.kitaru.ai/reference/python/client/) — fetch a single execution by ID
* [`list`](https://sdkdocs.kitaru.ai/reference/python/client/) — list executions
* [`latest`](https://sdkdocs.kitaru.ai/reference/python/client/) — the most recent execution
* [`logs`](https://sdkdocs.kitaru.ai/reference/python/client/) — retrieve runtime logs for an execution
* [`input`](https://sdkdocs.kitaru.ai/reference/python/client/) — provide input to an execution waiting on `kitaru.wait()`
* [`resume`](https://sdkdocs.kitaru.ai/reference/python/client/) — resume a waiting execution after input lands
* [`retry`](https://sdkdocs.kitaru.ai/reference/python/client/) — retry a failed execution
* [`cancel`](https://sdkdocs.kitaru.ai/reference/python/client/) — cancel a running execution
* [`replay`](https://sdkdocs.kitaru.ai/reference/python/client/) — replay from a checkpoint, optionally overriding cached outputs

## Artifacts

[`client.artifacts`](https://sdkdocs.kitaru.ai/reference/python/client/) browses and reads checkpoint outputs and saved artifacts.

## Deployments

[`client.deployments`](https://sdkdocs.kitaru.ai/reference/python/client/) invokes and inspects deployed flows:

* [`invoke`](https://sdkdocs.kitaru.ai/reference/python/client/) — start a new execution from a deployed flow (by name + tag/version)
* [`list`](https://sdkdocs.kitaru.ai/reference/python/client/) / [`get`](https://sdkdocs.kitaru.ai/reference/python/client/) — inspect available deployment routes

## Authentication

[`client.auth`](https://sdkdocs.kitaru.ai/reference/python/client/) manages service accounts and API keys for server access.

***

For complete signatures and the full method list, see the [Kitaru SDK reference](https://sdkdocs.kitaru.ai/reference/python/client/). For the command-line equivalents, see the [Kitaru CLI reference](https://sdkdocs.kitaru.ai/cli/).
