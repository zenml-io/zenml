---
description: Replay real agent runs against your real code with one thing changed, diff the results, and keep the wins — with Kitaru.
icon: robot
---

# Agents guide

This guide teaches production AI agents with [Kitaru](https://docs.zenml.io/kitaru), ZenML's sibling project for recording, replaying, and improving agents.

**Replay is the part other tooling can't do.** An eval re-grades outputs after the fact. Kitaru re-executes the actual run against your real code with one input swapped — a different model, a different prompt — while recorded tool calls are answered from the recording, so you find out what *would have happened* if you'd shipped the change. What arrives as a failing run leaves as a regression check on the next change.

The whole guide happens to one agent: **`returns-resolver`**, an autonomous returns agent from Kitaru's canonical example, with ten real runs and two policy violations hiding in them. By the end you'll have done three things to it:

1. **Recorded** its runs as sessions — imported from the Langfuse traces it already produced, with a one-wrapper native path as the alternative.
2. **Judged** them — cheap built-in evaluators to find the outliers, a structured investigation to record the human verdict, and a policy evaluator that turns that verdict into a versioned check.
3. **Improved** it — a stricter agent version replayed against frozen cohorts of exactly the runs that misbehaved (and the ones that mustn't regress), with the experiment's evidence doubling as a CI gate.

{% hint style="info" %}
A **session** is one recorded agent run — every model call and tool call as ordered nodes. ZenML and Kitaru split cleanly: ZenML is for ML pipelines; Kitaru is for agents, with its own lightweight server you can `docker compose up` in a minute.
{% endhint %}

## The learning path

The guide is in three parts. Parts 1 and 2 are the spine — they get you to replay, which is the whole point. Part 3 is a platform annex: the operating-at-scale machinery teams reach for once they run many agents on shared rails.

### Part 1 — Record

Stand up a local Kitaru server, register `returns-resolver` with its run command, and import its ten Langfuse-traced runs as tagged sessions — each model call and tool call a node. That recording is what Part 2 replays. Recording natively with the PydanticAI adapter is the one-wrapper alternative; the two paths are interchangeable.

* [Record an agent](01-durable-agent.md)

### Part 2 — Replay and improve

The differentiator. Find the two runs that broke the refund policy, record the support lead's judgment as an investigation, encode it as the `returns-policy` evaluator, freeze a target cohort (the violations) and a control cohort (the valid refunds that must not regress), and replay a stricter agent version against both — with the same evaluator versions judging baseline and replay. The whole loop is exposed over a CLI and an MCP server, so a coding agent can drive it and hill-climb on its own.

* [Replay and improve](replay-and-improve.md)

### Part 3 — Operate at scale

When several teams start building agents, the same platform questions come back every time: where logs live, how shell commands run without touching the host, how tools call internal services without handing the model raw credentials, how to pause for a human and resume from the same point, and how each team gets its own tools and rules without copying glue code.

Part 3 builds a small **internal agent harness platform** that answers those questions once. A team describes an agent with a `Profile` — its name, model, system prompt, allowed tools, allowed services, skill files, sandbox rules, and approval points — and shared platform code turns that profile into a runnable, durable agent. The result is reusable rails plus per-agent configuration, so Team A can build a support-triage agent and Team B a release-notes agent without both re-solving durability, logs, secrets, approvals, and safe command execution.

These stages each add one capability while keeping the earlier ones valid:

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Sandboxed command execution</strong></td><td>Put shell commands in a Docker sandbox with its own filesystem and network namespace, rather than running agent-generated commands on the host.</td><td><a href="02-sandbox.md">02-sandbox.md</a></td></tr><tr><td><strong>Operator-editable procedures</strong></td><td>Move repeatable agent instructions into skill markdown files, so teams can change procedures without burying every rule in the system prompt.</td><td><a href="03-skills.md">03-skills.md</a></td></tr><tr><td><strong>Credential isolation</strong></td><td>Keep secrets out of the worker. A separate proxy process holds credentials and adds auth headers for approved internal calls.</td><td><a href="04-credential-proxy.md">04-credential-proxy.md</a></td></tr><tr><td><strong>Typed service boundaries</strong></td><td>Route structured service requests through a typed dispatcher, so the platform can decide exactly which internal actions an agent may call.</td><td><a href="05-typed-services.md">05-typed-services.md</a></td></tr><tr><td><strong>Durable human approval</strong></td><td>Pause a run with <code>kitaru.wait()</code>, ask a human for a decision, and resume the same flow after the answer arrives.</td><td><a href="06-hitl.md">06-hitl.md</a></td></tr></tbody></table>

The platform stages are a **runnable local reference architecture**, not a turnkey enterprise platform. They don't ship your identity provider, policy engine, observability stack, or production secret store, and the sandbox is for local isolation, not a hostile-code security boundary. For which pieces are teaching stand-ins and what to harden first, see [Production notes and upgrade paths](production-notes.md).

<figure><img src="https://assets.kitaru.ai/docs/diagrams/agent-harness-platform-overview.png" alt="Architecture overview of the agent harness platform: profile-driven agents on shared platform rails."><figcaption></figcaption></figure>

{% hint style="warning" %}
Part 3 was written against an earlier Kitaru API and is being refreshed — the platform patterns (sandboxing, skills, credential isolation, typed services, human approval) stand, but treat its code samples as illustrative until this note disappears.
{% endhint %}

## Get the code

Parts 1 and 2 are a guided read of Kitaru's canonical example — every command runs from its directory, and the traces are checked in so no model key is needed to start:

```bash
git clone https://github.com/zenml-io/kitaru.git
cd kitaru/examples/canonical_example
```

The full source lives in [`examples/canonical_example/`](https://github.com/zenml-io/kitaru/tree/develop/examples/canonical_example): the returns agent, its mock commerce store, the checked-in Langfuse export, and an agent-guided walkthrough where a coding assistant drives the same loop. Part 3's harness platform lives separately in [`examples/end_to_end/agent_harness_platform/`](https://github.com/zenml-io/kitaru/tree/develop/examples/end_to_end/agent_harness_platform).

If you want the shortest path — wrap, record, replay, diff — start with the [Kitaru quickstart](https://docs.zenml.io/kitaru/getting-started/quickstart). Come back here for the guided record → replay → improve loop, and then the platform shape around it.
