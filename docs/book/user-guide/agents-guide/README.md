---
description: A runnable reference architecture for building an internal agent harness platform with Kitaru and PydanticAI
icon: robot
---

# Agents guide

This guide teaches durable AI agents with [Kitaru](https://docs.zenml.io/kitaru), ZenML's durable execution layer for agents. Where the other guides build ML pipelines, this one builds an internal agent platform — and the platform problems it solves are the ones every agent team eventually hits.

When one team builds one agent, the hard parts can hide in a notebook or a script. When several teams start building agents, the same platform questions come back every time:

- If an agent crashes halfway through a task, can it resume without paying for the same model call again?
- Where do logs live when someone needs to debug what happened yesterday?
- How does the agent run shell commands without touching the developer's laptop or the production host?
- How do tools call internal services without handing raw credentials to the model or the worker process?
- How do you stop an agent before it takes a risky action, wait for a human answer, and then continue from the same point?
- How do different teams get different tools, prompts, services, and safety rules without copying a pile of glue code?

This example is about those repeated platform problems. It shows one small internal agent harness platform where the shared machinery is reusable, and each individual agent is mostly configuration.

## What "internal agent harness platform" means here

In this example, an **internal agent harness platform** is not a place where agents magically appear. It is a small platform layer that takes an agent profile and produces a runnable agent with the same safety and operations rails every time.

Concretely, a team describes an agent with a `Profile`: its name, model, system prompt, allowed tools, allowed services, skill files, sandbox rules, and approval points. The platform code reads that profile and builds the agent around it. Kitaru supplies durable execution, so completed work can be reused after a retry. PydanticAI supplies the agent runtime. The example library supplies the platform seams around tools, sandboxes, credentials, typed service calls, and human approval.

The goal is that Team A can build a support-triage agent and Team B can build a release-notes agent without both teams re-solving durability, logs, secrets, approvals, and safe command execution from scratch.

## What this example is, and what it is not

This is a **runnable local reference architecture**. You can clone the repo, run the stages, and see each platform pattern in a concrete script. The stages are deliberately small: each one adds one new capability while keeping the older stages valid.

This also shows **forkable platform seams**. The credential proxy, typed service boundary, profile gates, sandbox, and human-in-the-loop pause are all shown as separate pieces because those are the pieces you would usually want to harden, replace, or connect to your own infrastructure.

This is **not** a turnkey enterprise platform. It does not ship your identity provider, policy engine, observability stack, deployment system, or production secret store. It is also **not** a hostile-code security boundary. The sandbox pattern is useful for local isolation and for showing where command execution belongs, but running untrusted code safely requires much more infrastructure and review than this example includes. For the full inventory of which pieces are teaching stand-ins and what to harden first, see [Production notes and upgrade paths](production-notes.md).

If you only want to make one function durable, start with the [Quickstart](https://docs.zenml.io/kitaru/getting-started/quickstart). Come back here when you want to see how the same Kitaru primitives fit into a larger internal platform shape.

## Architecture at a glance

<figure><img src="https://assets.kitaru.ai/docs/diagrams/agent-harness-platform-overview.png" alt="Architecture overview of the agent harness platform: profile-driven agents on shared platform rails."><figcaption></figcaption></figure>

The six patterns below build up this picture one capability at a time, in the order a platform team usually adds them.

## The six platform patterns

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Durable agent execution</strong></td><td>Build the smallest PydanticAI agent that runs inside a Kitaru flow, so completed turns can be reused after a retry instead of paid for twice.</td><td><a href="01-durable-agent.md">01-durable-agent.md</a></td></tr><tr><td><strong>Sandboxed command execution</strong></td><td>Put shell commands in a Docker sandbox with its own filesystem and network namespace, rather than running agent-generated commands on the host.</td><td><a href="02-sandbox.md">02-sandbox.md</a></td></tr><tr><td><strong>Operator-editable procedures</strong></td><td>Move repeatable agent instructions into skill markdown files, so teams can change procedures without burying every rule in the system prompt.</td><td><a href="03-skills.md">03-skills.md</a></td></tr><tr><td><strong>Credential isolation</strong></td><td>Keep secrets out of the worker. A separate proxy process holds credentials and adds auth headers for approved internal calls.</td><td><a href="04-credential-proxy.md">04-credential-proxy.md</a></td></tr><tr><td><strong>Typed service boundaries</strong></td><td>Route structured service requests through a typed dispatcher, so the platform can decide exactly which internal actions an agent may call.</td><td><a href="05-typed-services.md">05-typed-services.md</a></td></tr><tr><td><strong>Durable human approval</strong></td><td>Pause a run with <code>kitaru.wait()</code>, ask a human for a decision, and resume the same flow after the answer arrives.</td><td><a href="06-hitl.md">06-hitl.md</a></td></tr></tbody></table>

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

## What you will have at the end

By the end of the tour, you will have seen how to assemble:

- one `Profile` per agent, with clear gates for tools, services, skills, and approval points;
- a reusable `agent_harness_platform/` library that turns a profile into a durable PydanticAI agent;
- a sandboxed command path for shell work;
- a credential proxy path for service calls that need secrets;
- typed service handlers for approved internal actions; and
- durable human-in-the-loop pauses for decisions that should not be left to the model.

The demo prompts are intentionally generic. The point is not the toy task each stage performs. The point is the shape of the platform: shared rails once, many profile-driven agents on top.
