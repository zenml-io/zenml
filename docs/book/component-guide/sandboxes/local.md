---
description: A no-isolation subprocess sandbox for development and examples.
---

# Local Sandbox

The local sandbox flavor runs commands as `subprocess.Popen` on the same machine as the step, with the same OS user, full filesystem access, and full network access. **It provides no isolation.**

It is intended for:

- Quickstart / examples that should work without a Modal or other cloud account.
- Unit tests of code that consumes the `BaseSandbox` interface.
- Local development against the abstraction.

It is **not** intended for running untrusted LLM-generated code. For real isolation, use the [Modal](modal.md) flavor or wait for the upcoming container-based flavors (Agent Substrate, E2B, Daytona).

A loud warning is emitted on every `create_session()` call to make the no-isolation property impossible to miss.

## How to register

```bash
zenml sandbox register local-sb --flavor=local
zenml stack update --sandbox local-sb
```

No deps, no setup, no API keys. Works wherever Python runs.

## Settings

The Local sandbox inherits the base [`BaseSandboxSettings`](README.md#per-step-settings) — `environment`, `copy_local_env`, `timeout_seconds`, `forward_logs_to_step`. The `base_image` field is accepted for interface compatibility but ignored (there is no image concept locally) and logged as a warning if set.

Component-level `environment` and `secrets` (set via `zenml sandbox register --env ... --secret ...`) flow into every subprocess.

## What it doesn't support

| Feature | Local | Notes |
|---|---|---|
| `snapshot()` / `restore()` | ❌ | No state-capture primitive locally. |
| `attach(session_id)` | ❌ | Sessions are bound to the parent process; not re-attachable. |
| `upload_file` / `download_file` | ❌ | Files live in the session workdir already; use plain Python file I/O. |
| Streaming output | ✅ | `subprocess.PIPE` line-buffered. |
| `forward_logs_to_step` | ✅ | When True, lines route into the active ZenML `LoggingContext`. |
| `destroy()` | ✅ | Delegates to `close()`; removes the session workdir. |

## When to use it

Use the local flavor when:

- You want to try the Sandbox abstraction without setting up infrastructure.
- You're running an example that demonstrates the agent / sandbox split but doesn't care about isolation.
- You're writing a unit test that exercises a tool that consumes a `SandboxSession`.

Otherwise, use a containerized flavor.
