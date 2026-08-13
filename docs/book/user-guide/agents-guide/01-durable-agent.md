---
description: Bring a returns agent's real runs into Kitaru as replayable sessions — imported from Langfuse, under a registered agent version.
icon: bolt
---

# Record an agent

Everything in this guide happens to one agent: **`returns-resolver`**, an autonomous PydanticAI agent that resolves customer returns tickets. It investigates the order, checks the policy or shipment, takes one action — refund, replacement, or escalation — and drafts the reply. Its runs are the raw material; this page gets them into Kitaru as **sessions**: recordings of every model call and tool call, in order, that you can later replay.

The code is [`examples/canonical_example/`](https://github.com/zenml-io/kitaru/tree/develop/examples/canonical_example) in the Kitaru repo — ten synthetic customer emails, a mock in-memory commerce store, and a checked-in Langfuse trace export, so nothing here touches a real system or needs a model key to start. Run every command from that directory.

{% hint style="info" %}
A **session** is Kitaru's unit of recording. Sessions come from two places: recorded live by an [adapter](https://docs.zenml.io/kitaru/adapters/pydantic-ai) wrapped around your agent, or — as in this walkthrough — **imported from the traces you already collect**. The example's traces were real PydanticAI executions logged to Langfuse; Langfuse stays your system of record, Kitaru gets a runnable copy.
{% endhint %}

## Start Kitaru locally

```bash
cd examples/canonical_example
cp .env.example .env
set -a; source .env; set +a

docker compose -f ../../docker-compose.yml up -d --build
uv sync --extra cli --extra worker --extra pydantic-ai --extra examples
uv run kitaru login --local
uv run kitaru status
```

One small server (PostgreSQL + the Kitaru API + dashboard), one CLI connection. The server registers Kitaru's official importers and evaluators when it starts — confirm they're there:

```bash
uv run kitaru importer list       # kitaru/langfuse, and friends
uv run kitaru evaluator list      # kitaru/cost, kitaru/latency, kitaru/tool-call-patterns, ...
```

## Register the agent

Sessions belong to an **agent**, and replay later re-runs the agent's real code — so the registration carries the run command:

```bash
uv run kitaru agent register \
  returns-resolver \
  --command "python -m examples.canonical_example.agent" \
  --description "Resolve one synthetic returns or delivery ticket, execute one mock action, and draft the customer reply." \
  --display-version baseline-v1 \
  --working-dir ../.. \
  --timeout-seconds 180 \
  --tool lookup_order \
  --tool get_return_policy \
  --tool check_shipping \
  --tool issue_refund \
  --tool create_replacement \
  --tool escalate_to_human
```

That creates `returns-resolver` at version `1` — the baseline the traces came from. Start a worker in a second terminal (imports and replays execute on workers, in your environment, never on the server):

```bash
uv run kitaru worker start --name returns-example-worker
```

## Import the baseline runs

Ten real runs, exported from Langfuse as JSONL, imported under the exact agent version that produced them — and tagged, so every later step can select them as a group:

```bash
uv run kitaru session import \
  traces/langfuse-traces.jsonl \
  --importer kitaru/langfuse@latest \
  --agent returns-resolver@1 \
  --tag returns-baseline \
  --params '{"source_instance":"canonical-returns-example"}' \
  --media-type application/x-ndjson \
  --wait
```

The importer preserves the LLM calls, tool calls, tool results, final resolution, and source trace IDs. Check what landed:

```bash
uv run kitaru session list --tag returns-baseline --origin imported --size 20
uv run kitaru session nodes <session-id> --include-payloads --size 100
```

Each node is one model request or tool call with its inputs, outputs, and timing. That list is the recording — the raw material [replay](replay-and-improve.md) reads back.

## Recording natively instead

If you'd rather record at the source than import, wrap the agent once and every run streams to Kitaru live as it happens. The adapter ships as its own package (`uv add kitaru-pydantic-ai`):

```python
from kitaru_pydantic_ai import KitaruAgent

agent = KitaruAgent(base_agent, agent_id=AGENT_ID)   # base_agent: your plain PydanticAI Agent
```

Same sessions, same everything downstream — the two paths are interchangeable, and imported sessions replay exactly like recorded ones. The adapter contract is in the [Kitaru docs](https://docs.zenml.io/kitaru/adapters/pydantic-ai).

## What you have now

Ten real runs of `returns-resolver` are now faithful recordings on your Kitaru server. Two of them, you'll soon discover, did something the support lead considers unacceptable — and because the runs are sessions rather than transcripts, you won't just find the problem, you'll replay the fix against the exact runs that had it.

Continue to [Replay and improve](replay-and-improve.md).
