---
icon: code
---

# Python examples

Common patterns with the Kitaru Python SDK. For complete signatures, see the [Python SDK reference](https://sdkdocs.kitaru.ai/reference/python/). For the TypeScript client, see [How to use the SDK](https://docs.zenml.io/kitaru/get-help/sdks). For supported frameworks, see the [adapter overview](https://docs.zenml.io/kitaru/adapters/adapters).

## Record an agent's runs

Wrap an existing PydanticAI agent and every run is recorded as a session: each model call and tool call becomes a node. Each adapter ships as its own distribution, installed alongside `kitaru`. Here, install it with `uv add kitaru-pydantic-ai`:

```python
import os
import uuid

from pydantic_ai import Agent
from kitaru_pydantic_ai import KitaruAgent

base_agent = Agent("openai:gpt-5.4", system_prompt="You resolve support tickets.")

agent = KitaruAgent(base_agent, agent_id=uuid.UUID(os.environ["KITARU_AGENT_ID"]))
result = agent.run_sync("Refund order #4821; the card reader was double-charged.")
```

## Inspect sessions

```python
import asyncio

from kitaru.client import KitaruAPIClient
from kitaru.api_models.v1.session import SessionListParams
from kitaru.api_models.v1.session_node import SessionNodeListParams


async def main() -> None:
    async with KitaruAPIClient() as client:
        sessions = await client.sessions.list(SessionListParams(size=5))
        if not sessions.items:
            return
        baseline_session_id = sessions.items[0].id
        nodes = await client.sessions.list_nodes(
            baseline_session_id, SessionNodeListParams(include_payloads=True)
        )
        print(baseline_session_id, len(nodes.items))


asyncio.run(main())
```

## Replay with one thing changed

Answer tool calls from the recorded session, swap the model, and run the same evaluator on both sides:

```python
import asyncio
import os
import uuid

from kitaru.client import KitaruAPIClient
from kitaru.api_models.v1.replay import ReplayCreateRequest
from kitaru.api_models.v1.replay_config import (
    EvaluatorConfig,
    HistoryConfig,
    ReplayOverride,
    ToolPolicy,
)


async def main() -> None:
    baseline_session_id = uuid.UUID(os.environ["KITARU_BASELINE_SESSION_ID"])
    async with KitaruAPIClient() as client:
        replay = await client.replays.create(
            ReplayCreateRequest(
                baseline_session_id=baseline_session_id,
                override=ReplayOverride(
                    model={"openai:gpt-5.4": "openai:gpt-5-nano"}
                ),
                evaluators=[EvaluatorConfig(evaluator="refund-check")],
                tool_policy=ToolPolicy(
                    default=HistoryConfig(scope="baseline", on_miss="fail")
                ),
                evaluate_baselines=True,
            )
        )
        print(replay.id, replay.job_id)


asyncio.run(main())
```

The full walkthrough, from recording through replaying cohorts and experiments, is the [Kitaru quickstart](https://docs.zenml.io/kitaru/getting-started/quickstart).
