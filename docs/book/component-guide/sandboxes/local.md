---
description: A no-isolation subprocess sandbox for development and examples.
---

# Local Sandbox

The local sandbox flavor runs commands as `subprocess.Popen` on the same machine as the step, with the same OS user, full filesystem access, and full network access. **It provides no isolation.**

It is intended for:

- Quickstart / examples that should work without a Modal or other cloud account.
- Unit tests of code that consumes the `BaseSandbox` interface.
- Local development against the abstraction.

It is **not** intended for running untrusted LLM-generated code. For real isolation, use a different sandbox flavor.

## How to register

```bash
zenml sandbox register local-sb --flavor=local
zenml stack update --sandbox local-sb
```

## Settings

The Local sandbox inherits `BaseSandboxSettings` and adds `forward_env`.

- `sandbox_environment`: explicit environment variables to set inside the subprocess.
- `forward_env`: which parent-process variables are forwarded into the session. Set `forward_env=True` to forward the entire parent environment, `False` to forward nothing, or pass a list of names to forward exactly those. It defaults to a set that keeps command resolution and UTF-8 stdio working: `PATH`, `HOME`, `LANG`, `LC_ALL`, `TMPDIR`, `TERM`.

Secrets in the parent environment stay isolated from the session unless `forward_env` is `True` or names them explicitly. `sandbox_environment` is layered on top and overrides forwarded variables on a key collision.

## What it doesn't support

| Feature | Local | Notes |
|---|---|---|
| `snapshot()` / `restore()` | ❌ | No state-capture primitive locally. |
| `attach(session_id)` | ❌ | Sessions are bound to the parent process; not re-attachable. |
| `upload_file` / `download_file` | ❌ | Files live in the session workdir already; use plain Python file I/O. |
| Streaming output | ✅ | `subprocess.PIPE` line-buffered. |
| Sandbox log forwarding | ✅ | Each `exec` emits a `$ <command>` marker plus stdout/stderr lines + an `OK`/`FAIL exit code <code>` trailer into the step's `sandbox:<id>` log source. |
| `destroy()` | ✅ | Delegates to `close()`; removes the session workdir. |

## When to use it

Use the local flavor when:

- You want to try the Sandbox abstraction without setting up infrastructure.
- You're running an example that demonstrates the agent / sandbox split but doesn't care about isolation.
- You're writing a unit test that exercises a tool that consumes a `SandboxSession`.

Otherwise, use a containerized flavor.
