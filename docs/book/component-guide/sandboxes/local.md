---
description: A no-isolation subprocess sandbox for development and examples.
---

# Local Sandbox

The local sandbox flavor runs commands as `subprocess.Popen` on the same machine as the step, with the same OS user, full filesystem access, and full network access. **It provides no isolation.**

It is intended for:

- Quickstart / examples that should work without a Modal or other cloud account.
- Unit tests of code that consumes the `BaseSandbox` interface.
- Local development against the abstraction.

It is **not** intended for running untrusted LLM-generated code. For real isolation, use a container-based flavor (Modal, Agent Substrate, E2B, Daytona) once they ship.

A loud warning is emitted on every `create_session()` call to make the no-isolation property impossible to miss.

## How to register

```bash
zenml sandbox register local-sb --flavor=local
zenml stack update --sandbox local-sb
```

No deps, no setup, no API keys. Works wherever Python runs.

## Settings

The Local sandbox inherits the base `BaseSandboxSettings` (`environment`, `copy_local_env`). `copy_local_env` defaults to `True` so PATH/HOME flow into the subprocess. Since there is no isolation, this matches user expectation, but it does mean the executed code sees every variable in your local environment (credentials, tokens). Set `copy_local_env=False` when running untrusted code.

Component-level `environment` and `secrets` (set via `zenml sandbox register --env ... --secret ...`) flow into every subprocess.

## What it doesn't support

| Feature | Local | Notes |
|---|---|---|
| `snapshot()` / `restore()` | ❌ | No state-capture primitive locally. |
| `attach(session_id)` | ❌ | Sessions are bound to the parent process; not re-attachable. |
| `upload_file` / `download_file` | ❌ | Files live in the session workdir already; use plain Python file I/O. |
| Streaming output | ✅ | `subprocess.PIPE` line-buffered. |
| Sandbox log forwarding | ✅ | Each `exec` emits a `$ <command>` marker plus stdout/stderr lines + a `✓ exit <code>` trailer into the step's `sandbox:<id>` log source. |
| `destroy()` | ✅ | Delegates to `close()`; removes the session workdir. |

## When to use it

Use the local flavor when:

- You want to try the Sandbox abstraction without setting up infrastructure.
- You're running an example that demonstrates the agent / sandbox split but doesn't care about isolation.
- You're writing a unit test that exercises a tool that consumes a `SandboxSession`.

Otherwise, use a containerized flavor.
