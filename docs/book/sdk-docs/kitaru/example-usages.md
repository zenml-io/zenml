---
icon: code
---

# Example usages

Common patterns with the Kitaru Python SDK. For the complete reference, see [sdkdocs.kitaru.ai](https://sdkdocs.kitaru.ai); for conceptual guides, see the [Kitaru docs](https://docs.zenml.io/kitaru).

## Record an agent's runs

Wrap an existing PydanticAI agent and every run is recorded as a session — each model call and tool call a node:

```python
import os
import uuid

from pydantic_ai import Agent
from kitaru.adapters.pydantic_ai import KitaruAgent

base_agent = Agent("openai:gpt-5.4", system_prompt="You resolve support tickets.")

agent = KitaruAgent(base_agent, agent_id=uuid.UUID(os.environ["KITARU_AGENT_ID"]))
result = agent.run_sync("Refund order #4821 — the card reader was double-charged.")
```

## Inspect sessions

```python
from kitaru.client import KitaruAPIClient
from kitaru.api_models.v1.session import SessionListParams

client = KitaruAPIClient()
sessions = await client.sessions.list(SessionListParams(size=5))
nodes = await client.sessions.list_nodes(sessions.items[0].id, include_payloads=True)
```

## Replay with one thing changed

Recorded tool calls answered from the session, the model swapped, evaluations on both sides:

```python
from kitaru.api_models.v1.replay import ReplayCreateRequest, ReplayOverride
from kitaru.api_models.v1.replay_config import (
    EvaluatorConfig, HistoryConfig, ToolPolicy,
)

replay = await client.replays.create(
    ReplayCreateRequest(
        baseline_session_id=session_id,
        override=ReplayOverride(model={"openai:gpt-5.4": "openai:gpt-5-nano"}),
        evaluators=[EvaluatorConfig(evaluator="refund-check")],
        tool_policy=ToolPolicy(default=HistoryConfig(scope="baseline", on_miss="fail")),
        evaluate_baselines=True,
    )
)
```

The full walkthrough — recording, replaying, cohorts, experiments — is the [Kitaru quickstart](https://docs.zenml.io/kitaru/getting-started/quickstart).
