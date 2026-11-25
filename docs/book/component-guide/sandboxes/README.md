---
description: Isolated code execution for AI agents and tool-use loops.
icon: box-archive
---

# Sandboxes

A **Sandbox** is a stack component that provides an isolated environment (container, microVM, or pod) in which a ZenML step can execute code. It's primarily designed for AI-agent workloads: an agent running inside a step uses the active stack's Sandbox to execute generated code as a tool, possibly across many turns of an agent loop.

A Sandbox is fundamentally different from a [Step Operator](../step-operators/README.md):

- A **Step Operator** runs the step itself on a remote backend.
- A **Sandbox** is a tool the step *consumes*. The step still runs wherever the orchestrator placed it, and you can run code in the sandbox from within your step code.

The two compose: a step running on, say, the SageMaker step operator can still grab the active stack's Sandbox and use it for code execution.

## Concepts

| Term | What it is |
|---|---|
| **Sandbox component** (`BaseSandbox`) | The stack-component entity. Long-lived, configured once, registered in your stack. One Sandbox component can mint many live Sessions. |
| **Sandbox Session** (`SandboxSession`) | A live, bounded interaction with a single isolated environment. Has an `id`, accepts many `exec` calls, can be snapshotted, is explicitly closed. |
| **Sandbox Process** (`SandboxProcess`) | A handle to one running command inside a Session. Exposes line-delimited stdout/stderr iterators, `wait()` for the exit code, `kill()` to terminate. |
| **Sandbox Snapshot** (`SandboxSnapshot`) | A serializable, provider-specific handle to a captured Session state. Round-trips through `session.create_snapshot()` and `sandbox.restore(snapshot)`. |

## How to use it from a step

A Sandbox is reached for from inside a step via the active stack:

```python
from zenml import step
from zenml.client import Client


@step
def agent_step(prompt: str) -> str:
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError("No sandbox configured in the active stack.")

    with sandbox.create_session() as session:
        process = session.exec(["python", "-c", "print(1 + 1)"])
        output = "".join(process.stdout())
        process.wait()
        return output
```

If your stack contains more than one Sandbox component, address them by name through `Client().active_stack.sandboxes` (a `Dict[str, BaseSandbox]`). The `.sandbox` accessor returns the default (first attached).

### Streaming output

`SandboxProcess.stdout()` and `stderr()` yield strings one line at a time as the underlying command produces them — the standard pattern for streaming an agent's tool output back to a UI or to the step logs.

### Snapshots, restore, and attach

A Session can optionally be snapshotted (provider-dependent — not all backends support full state capture). The returned `SandboxSnapshot` is a Pydantic model that's safe to persist as a ZenML artifact:

```python
snap = session.create_snapshot()
zenml.save_artifact(snap, name="agent_checkpoint")
# ... later, possibly in a different pipeline run:
snap = zenml.load_artifact("agent_checkpoint")
session = stack.sandbox.restore(snap)        # new session, state restored
```

`restore` always returns a *new* Session (fresh `id`); the original Session is unaffected.

For the common subagent / cross-pipeline reuse case where the original Session is still alive, use `attach()` instead — no snapshot required, the parent just persists the session id as an artifact and the child reconnects to it:

```python
# Parent step
session_id = session.id
zenml.save_artifact(session_id, name="agent_session")

# Child step (possibly in a child pipeline run)
session = stack.sandbox.attach(zenml.load_artifact("agent_session"))
```

### Closing vs destroying

- `session.close()` releases the local handle. The sandbox **keeps running** on the provider until its TTL expires. Use this when a subagent or follow-up step might still want to `attach` to the same Session.
- `session.destroy()` terminates the sandbox on the provider. After this, the `id` is invalid and `attach()` will fail.

ZenML does **not** auto-close Sessions on step exit. Either use a `with` block (`__exit__` calls `close()`) or call `close()` / `destroy()` explicitly.

## Configuration

### Per-step settings

Step writers can configure sandbox behavior on individual `@step` invocations via `BaseSandboxSettings` (or a flavor-specific subclass):

| Setting | Purpose |
|---|---|
| `sandbox_environment` | Environment variables to set inside the Session. |

Flavors that boot a container or microVM add their own settings (for example image selection and a provider TTL) on a flavor-specific `BaseSandboxSettings` subclass.

### Sandbox logs

Sandbox stdout/stderr automatically lands on the active step as a dedicated `sandbox:<session_id>` log source. Each `session.exec(...)` writes a `$ <command>` marker, then the process output (stdout at INFO, stderr at ERROR), then a trailing `OK`/`FAIL exit code <code> in <seconds>s` marker — reads like a shell session. ZenML's own step-level Python logger calls stay in the regular `step` source: the sandbox source is dedicated to actual sandbox-execution events, no false attribution.

Multi-session steps don't clobber: each session's metadata (flavor, dashboard URL when the flavor exposes one) is keyed by session id (`sandbox.<id>.flavor`, `sandbox.<id>.dashboard_url`).

## Security considerations

Every value you put in a Session's environment (`sandbox_environment`) is **readable by code running inside the Session**. If you run LLM-generated code in the Sandbox and care about credential isolation, treat the Session environment as visible to the agent.

## Available flavors

- **[Local](local.md)** — subprocess-based; **no isolation**; built-in. Intended for examples, unit tests, and development against the abstraction.
- **[Kubernetes](kubernetes.md)** — pod-backed sessions executed through Kubernetes exec.

## Develop a custom Sandbox

To build a flavor for a new backend, subclass `BaseSandbox`, `SandboxSession`, `SandboxProcess`, and optionally `SandboxSnapshot`. The minimal required surface is:

- `BaseSandbox.create_session(settings=None) -> SandboxSession`
- `SandboxSession.exec(...) -> SandboxProcess`
- `SandboxSession.close()`
- `SandboxProcess.stdout()` / `stderr()` / `wait()` / `kill()` / `exit_code`

Everything else (`attach`, `create_snapshot`, `restore`, `aexec`, `upload_file`, `download_file`, `destroy`) is opt-in — the base raises `NotImplementedError` and you override only what your backend supports. Register your flavor via the standard `Integration.flavors()` hook.
