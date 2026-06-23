---
description: Which pieces of the agent harness tour are teaching stand-ins, where each one plugs into production, and what to harden before you rely on the pattern
icon: shield-halved
---

# Production notes and upgrade paths

Every stage in this tour runs on a laptop, so the example uses stand-ins: Docker for the sandbox, local markdown for procedures, a self-signed proxy and mock HTTP services for credentials and internal calls. The stand-ins are good enough to run and read, but they are not the part you would ship.

The part worth keeping is the shape. Each capability sits behind a small, named swap point, so you can replace the laptop version with something your platform team trusts without rewriting the agent. This page is the inventory: each teaching stand-in, the production piece it stands in for, and the seam where you swap.

Kitaru's own primitives do not change. Durable checkpoints, wait/resume, and replay are the same in production as on your laptop — they are the durable execution that makes the run/replay/improve loop faithful, not a thing you re-implement. The production work is configuring the runtime and storage for your environment, then hardening the platform around those primitives. Everything else on this page lives in the example's forkable `agent_harness_platform/` library, not in Kitaru itself.

{% hint style="warning" %}
This example is a runnable reference architecture, not a hardened platform. As shipped it cannot safely contain code that is actively trying to break out, and it is not a turnkey production system. Treat the sections below as a starting checklist, not a guarantee.
{% endhint %}

## Stand-ins at a glance

| Capability | Tutorial stand-in | What a fork swaps in | The seam |
|---|---|---|---|
| Durable execution (Stage 1) | `checkpoint_strategy="turn"` for readable logs | The `KitaruAgent` default: `checkpoint_strategy="calls"` (one checkpoint per model request and tool call) | the `checkpoint_strategy` setting |
| Command sandbox (Stage 2) | `DockerSandbox` on your laptop | Stronger isolation for risky commands | `run(command) -> ExecResult` |
| Agent procedures (Stage 3) | `LocalSkillSource` over local markdown | A reviewed, versioned procedure store | `SkillSource.resolve() -> Path` |
| Service credentials (Stage 4) | mitmproxy + self-signed CA on a shared Docker network | Network isolation, proxy authorization, and production secret handling | `SandboxProxyRule` plus the proxy container |
| Structured actions (Stage 5) | Typed handlers calling `mocks/server.py` | Real internal services with per-action authorization | the `exec_service` registry |
| Human approval (Stage 6) | Local terminal prompt | Dashboard, CLI, or REST answered by a known operator | `kitaru.wait()` |

The rest of this page walks each row in tour order.

## Durable execution

The tour passes `checkpoint_strategy="turn"` so each agent turn is one log block you can point at while learning. A real fork usually drops it and takes the `KitaruAgent` default, `checkpoint_strategy="calls"`, where every model request and every tool call gets its own checkpoint and cache key. A flow that crashed after the third model request then resumes by replaying only the calls after the third.

The durability story is identical either way — and so is replay. The only change is how finely work is cached and how finely it shows on the dashboard. Nothing about Kitaru itself changes. See [Stage 1](01-durable-agent.md).

## Sandbox isolation

The `exec` tool depends on one method: `run(command) -> ExecResult`. `DockerSandbox` is the laptop implementation. Docker gives a real filesystem, process, and network boundary, which contains an agent that runs a bad `rm`. It is not a wall against code actively trying to break out, because the container shares the host kernel. When the commands matter, swap the backend at that one seam. These options generally move toward stronger isolation, but the right choice depends on your threat model, workload, and platform:

- [Docker](https://docs.docker.com/engine/security/) is the easy local default and stops accidental damage to the host.
- [gVisor](https://gvisor.dev/) runs each container against a user-space kernel, so syscalls hit gVisor before the host kernel. It keeps the container-shaped experience while adding stronger isolation.
- [Kata Containers](https://katacontainers.io/) wraps each container in a lightweight VM, so a kernel escape lands in the VM rather than on the host.
- [Firecracker](https://firecracker-microvm.github.io/) gives each run its own minimal microVM with a small attack surface (the technology behind AWS Lambda).
- Hosted sandboxes such as [E2B](https://e2b.dev/), [Modal](https://modal.com/products/sandboxes), or [Daytona](https://www.daytona.io/) run commands on isolated infrastructure, so nothing executes on your machine.
- [WebAssembly](https://webassembly.org/) isolates by default but is a poor fit for arbitrary `bash`; it suits cases where you can constrain what the agent runs.

The agent's tool wiring does not change when you swap, because the swap happens behind `run(command)`. See [Stage 2](02-sandbox.md).

## Skill sources

Procedures live behind `SkillSource`, an alias with a single method, `resolve() -> Path`. The `skill` tool only ever sees a directory of markdown; it never learns where that directory came from. The example ships `LocalSkillSource` for local files. Common fork targets:

- `GitRepoSkillSource` clones a versioned skill repo at flow start, so procedures are reviewed through pull requests and shared across teammates and running agents.
- `InlineMarkdownSkillSource` bakes the markdown straight into the `Profile`, which suits one-off agents, tests, or skills generated by another flow.
- Object storage, Kitaru artifacts, or a container-image bake cover stricter deployment shapes.

Be clear about the boundary. Kitaru supplies the durable flow the read-and-act cycle runs inside. The example library supplies `Profile.skill_source`, `SkillSource`, `LocalSkillSource`, profile-gated access to the tool, and the swappable source seam. Kitaru does **not** ship skill versioning, review, diffs, change history, or any UI that surfaces edits. Those are real concerns, and a `SkillSource` subclass is where your fork adds them. See [Stage 3](03-skills.md).

## Credential architecture

Stage 4 draws one trust boundary: the credential that authorizes a call lives in the proxy container, and the process running model-chosen commands lives in the worker. The boundary is the lesson. The implementation around it is built for a laptop and needs hardening before you lean on it.

What is a stand-in:

- The sandbox, proxy, and mock all share one Docker network, so the worker can reach the upstream host directly. That direct call fails with `401` because only the proxy can add the `Authorization` header — but the network path itself is open.
- The per-run proxy bearer sits in the worker's `http_proxy` environment variable, so a prompt-injected agent can read it. That bearer only gets a request through the proxy; it does not limit which requests the worker may make.
- Network reachability is not authentication. This pattern stops raw-token exfiltration, but on its own it is not per-path or per-method authorization.

What a production fork adds:

- per-role networks, with the worker isolated (optionally under egress policies) and upstreams reachable only from the proxy;
- host, path, and method allowlists on the proxy, or per-agent rules, so reaching the proxy does not grant arbitrary authenticated calls to an allowed host;
- credentials mounted as files rather than environment variables;
- mTLS in place of the per-run basic-auth-as-bearer;
- the persistent-shell completion signal on a side channel rather than mixed into stdout.

The seam is `SandboxProxyRule` plus the proxy container. See [Stage 4](04-credential-proxy.md).

## Service boundaries

`exec` is for shell-shaped work the agent reasons about as command output. `exec_service` is for structured host-side actions: look up a record, file a ticket, publish a summary, call an internal control plane. The typed boundary is the natural place to decide which agent may call which action. In the tour the handlers hit a local mock, and each one holds a single secret resolved from a Kitaru secret. A fork:

- swaps the mock handlers for real internal services;
- adds per-service authorization at the boundary, so "may this agent call this action" is answered in one place rather than trusted to the model;
- keeps shell work on `exec` and structured work on `exec_service`, instead of letting the model hand-assemble `curl` for actions that have a defined input and output.

Adding a service is three files: a handler, an args and result Pydantic pair, and an `ALL_SERVICES` entry. The tool surface and its description update from the profile's `allowed_services`. See [Stage 5](05-typed-services.md).

## Human approval and operator surface

On a laptop the operator answers `ask_question` at the same terminal. On a server the same `kitaru.wait()` record is answered through the dashboard, CLI, or REST API — the non-interactive run in Stage 6 is already that shape. The durable pause works the same way in production. `kitaru.wait()` provides the pause/resume mechanism; the operator surface around it enforces identity, authentication, authorization, and audit. A real platform also adds:

- treat operator input as untrusted and escape it before it reaches anything that interprets bytes (an HTML renderer, a shell, SQL); the example passes it through verbatim;
- record who approved what when your environment needs an audit trail of approver identity and time;
- when you drop the teaching-only `checkpoint_strategy="turn"` for the default `checkpoint_strategy="calls"`, exempt wait-bearing tools so they still run at flow scope, for example `tool_checkpoint_config_by_name={"ask_question": False}`.

See [Stage 6](06-hitl.md).

## What to harden before you rely on this

If you adopt this pattern for real work, work through these in roughly this order — worst blast radius first:

1. **Isolation for command execution.** If the agent can run model-authored or untrusted commands that matter, replace Docker with a stronger backend (gVisor, Kata, Firecracker, or a hosted sandbox). Docker alone is not a hostile-code boundary.
2. **The credential and network boundary.** Put the worker on its own network, add host, path, and method allowlists to the proxy, move secrets to files or a secret manager, and prefer mTLS. The shared Docker network and the visible proxy bearer are tutorial shortcuts.
3. **Authorization at the service boundary.** Decide which agent may call which `exec_service` action, and enforce it in one place rather than trusting the model to stay in bounds.
4. **Input that crosses a trust boundary.** Treat operator answers and service arguments as untrusted data. Validate and escape them before they reach anything that interprets bytes, such as HTML, SQL, or a shell.
5. **Model-authored commands.** Do not rely on escaping to make arbitrary shell commands safe. Use sandboxing, command allowlists, typed service alternatives, and careful action design.
6. **Side-effect idempotency.** Design shell and API mutations around replay and cache behavior. Actions such as `git push`, `curl POST`, database writes, ticket creation, and webhook posts need operation IDs, idempotency keys, deduplication, or checkpoint boundaries that prevent accidental double or missing effects.
7. **Procedure governance.** Add the review, provenance, and version pinning that Kitaru does not ship for skills, on whichever `SkillSource` you choose.
8. **Checkpoint and log data governance.** Treat checkpoint data, tool arguments and results, model messages, wait answers, and logs as potentially sensitive. Add retention, access control, redaction, and deletion or export rules where your environment requires them.
9. **The platform around all of this.** Identity, policy, observability, deployment, and a production secret store are out of scope for the example. They are yours to bring.

Kitaru's job in this list is narrow: durable execution, wait/resume, and replay survive process failure for you once the runtime and storage are configured for your environment. The rest is platform work — and the point of the example is that each item above has an obvious place to land.
