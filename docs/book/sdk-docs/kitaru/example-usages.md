---
icon: code
---

# Example usages

Common patterns with the Kitaru Python SDK. For the complete reference, see [sdkdocs.kitaru.ai](https://sdkdocs.kitaru.ai); for conceptual guides, see the [Kitaru docs](https://docs.zenml.io/kitaru).

## Define and run a durable flow

A flow is the outer durable boundary; checkpoints inside it are the persisted replay boundaries.

```python
import kitaru
from kitaru import checkpoint, flow

@checkpoint
def research(topic: str) -> str:
    return kitaru.llm(f"Summarize {topic} in two sentences.")

@checkpoint
def draft_report(summary: str) -> str:
    return kitaru.llm(f"Write a short report based on: {summary}")

@flow
def research_agent(topic: str) -> str:
    summary = research(topic)
    return draft_report(summary)

if __name__ == "__main__":
    handle = research_agent.run(topic="durable execution for AI agents")
    print(handle.wait())
```

If the flow fails at `draft_report`, replaying it reuses the recorded `research` output instead of re-running it.

## Inspect executions with `KitaruClient`

```python
import kitaru

client = kitaru.KitaruClient()
execution = client.executions.get("<exec-id>")
print(execution.status)
```

<!-- More examples (wait/resume, replay with overrides, deployments) to follow. -->
