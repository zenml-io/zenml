---
description: Replay real agent runs against your real code with one thing changed, diff the results, and keep the wins — with Kitaru.
icon: robot
---

# Agents guide

This guide teaches production AI agents with [Kitaru](https://docs.zenml.io/kitaru), ZenML's sibling project for recording, replaying, and improving agents.

**Replay is the part other tooling can't do.** An eval re-scores outputs after the fact. Kitaru re-executes the actual run from a durable checkpoint with one input swapped — a different model, a different prompt — so you find out what *would have happened* if you'd shipped the change, against your real code rather than a rescored transcript. What arrives as a failing run leaves as a regression check on the next change.

By the end you'll be able to do three things:

1. **Replay** a real run with one thing changed and diff the result against a faithful baseline.
2. **Improve** the agent by rolling the winning change across a filtered set of recent runs and keeping the version that holds up on cost, latency, and the decisions that matter — with the diff matrix as your regression evidence.
3. **Run** an agent durably — the beat that mints the recording. Every model and tool call becomes a durable checkpoint, which doubles as crash recovery and as the raw material replay reads back.

{% hint style="info" %}
A Kitaru **flow** is a dynamic ZenML pipeline. A **checkpoint** is like a step. Agents and pipelines run on the same stacks, the same server, the same dashboard.
{% endhint %}

## The learning path

The guide is in three parts. Parts 1 and 2 are the spine — they get you to replay, which is the whole point. Part 3 is a platform annex: the operating-at-scale machinery teams reach for once they run many agents on shared rails.

### Part 1 — Record

Wrap a PydanticAI agent in a Kitaru flow so every model call and tool call becomes a durable checkpoint. That recording is what Part 2 replays; the same checkpoints double as crash recovery, so a retry resumes from where the crash hit instead of paying for the whole run twice. This is how the recording gets made.

* [Record a durable agent](01-durable-agent.md)

### Part 2 — Replay and improve

The differentiator. Take a recorded run, reproduce it faithfully as a control, then replay it again with exactly one thing changed and diff the two. Because the baseline reproduced, the difference is your change, not replay noise. Then scale that decision across a filtered set of runs and read cost, latency, and whether the decisions held across the batch. Replay and diff are exposed over a CLI and an MCP server, so a coding agent can drive the loop and hill-climb on its own.

* [Replay and improve](replay-and-improve.md)

### Part 3 — Operate at scale

When several teams start building agents, the same platform questions come back every time: where logs live, how shell commands run without touching the host, how tools call internal services without handing the model raw credentials, how to pause for a human and resume from the same point, and how each team gets its own tools and rules without copying glue code.

Part 3 builds a small **internal agent harness platform** that answers those questions once. A team describes an agent with a `Profile` — its name, model, system prompt, allowed tools, allowed services, skill files, sandbox rules, and approval points — and shared platform code turns that profile into a runnable, durable agent. The result is reusable rails plus per-agent configuration, so Team A can build a support-triage agent and Team B a release-notes agent without both re-solving durability, logs, secrets, approvals, and safe command execution.

These stages each add one capability while keeping the earlier ones valid:

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Sandboxed command execution</strong></td><td>Put shell commands in a Docker sandbox with its own filesystem and network namespace, rather than running agent-generated commands on the host.</td><td><a href="02-sandbox.md">02-sandbox.md</a></td></tr><tr><td><strong>Operator-editable procedures</strong></td><td>Move repeatable agent instructions into skill markdown files, so teams can change procedures without burying every rule in the system prompt.</td><td><a href="03-skills.md">03-skills.md</a></td></tr><tr><td><strong>Credential isolation</strong></td><td>Keep secrets out of the worker. A separate proxy process holds credentials and adds auth headers for approved internal calls.</td><td><a href="04-credential-proxy.md">04-credential-proxy.md</a></td></tr><tr><td><strong>Typed service boundaries</strong></td><td>Route structured service requests through a typed dispatcher, so the platform can decide exactly which internal actions an agent may call.</td><td><a href="05-typed-services.md">05-typed-services.md</a></td></tr><tr><td><strong>Durable human approval</strong></td><td>Pause a run with <code>kitaru.wait()</code>, ask a human for a decision, and resume the same flow after the answer arrives.</td><td><a href="06-hitl.md">06-hitl.md</a></td></tr></tbody></table>

The platform stages are a **runnable local reference architecture**, not a turnkey enterprise platform. They don't ship your identity provider, policy engine, observability stack, or production secret store, and the sandbox is for local isolation, not a hostile-code security boundary. For which pieces are teaching stand-ins and what to harden first, see [Production notes and upgrade paths](production-notes.md).

<figure><img src="https://assets.kitaru.ai/docs/diagrams/agent-harness-platform-overview.png" alt="Architecture overview of the agent harness platform: profile-driven agents on shared platform rails."><figcaption></figcaption></figure>

## Get the code

The local tour needs Docker and one model-provider API key. The wiki and webhook services are mocked locally.

```bash
git clone https://github.com/zenml-io/kitaru.git
cd kitaru/examples/end_to_end/agent_harness_platform
uv sync
uv run kitaru init
export OPENAI_API_KEY=sk-...
uv run python stage_1_basic_agent.py
```

The full source lives in [`examples/end_to_end/agent_harness_platform/`](https://github.com/zenml-io/kitaru/tree/develop/examples/end_to_end/agent_harness_platform) on GitHub. It includes the runnable stage files, the reusable `agent_harness_platform/` library, mocks, skills, and Dockerfiles.

If you only want to make one function durable, start with the [Kitaru quickstart](https://docs.zenml.io/kitaru/getting-started/quickstart). Come back here when you want the full run → replay → improve loop, and then the platform shape around it.
