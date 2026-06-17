---
description: Running agent code in Modal sandboxes.
---

# Modal Sandbox

[Modal](https://modal.com) provides fast-booting, ephemeral compute containers ideal for running LLM-generated code as part of an AI-agent step. The Modal Sandbox flavor wraps Modal's `Sandbox` / `ContainerProcess` / `Image` primitives in ZenML's [Sandbox](README.md) interface, so an agent inside a step can `exec()` commands, stream output, snapshot the filesystem, reattach by id, and tear down — all without leaving ZenML.

### When to use it

Use the Modal Sandbox flavor when:

- Your agent needs sub-second cold starts for ephemeral code execution.
- You want filesystem snapshots that boot back into a fresh `Sandbox` on demand.
- You're already on Modal (e.g. using the [Modal step operator](../step-operators/modal.md)) and want to share infrastructure with your sandbox workloads.

### How to deploy it

1. [Sign up for a Modal account](https://modal.com/signup).
2. Install the Modal CLI and authenticate:
   ```bash
   pip install modal && modal setup
   ```
3. Install the ZenML Modal integration:
   ```bash
   zenml integration install modal
   ```

### How to register the component

```bash
zenml sandbox register my-modal-sandbox \
    --flavor=modal \
    --app_name=my-agent-app
```

Component-level `--env` and ZenML-stored `--secret` values are injected into your **step process** environment (where your agent framework runs), not into the sandbox container — see the [Environment Variables docs](https://docs.zenml.io/concepts/environment-variables#configuring-environment-variables-on-stack-components). Env vars for code running *inside* the sandbox go through the `sandbox_environment` setting instead:

```bash
zenml sandbox register my-modal-sandbox --flavor=modal ... \
    --env='{"LOG_LEVEL": "debug"}' \
    --secret=openai_creds
```

Then attach it to your stack:

```bash
zenml stack update --sandbox my-modal-sandbox
```

### Settings reference

`ModalSandboxSettings` (override on individual `@step` decorations):

| Field | Purpose |
|---|---|
| `image` | Docker image to boot the Sandbox from. Any registry reference Modal can pull, e.g. `python:3.11-slim` (the default) or `my-registry/my-image:tag`. |
| `sandbox_environment` | Env vars to set in the Session, injected at Sandbox create time. |
| `timeout` | Sandbox lifetime in seconds, forwarded to Modal's `Sandbox.create(timeout=)`. Also honored on `restore()`. |
| `cpu` | CPU cores requested for the sandbox, e.g. `2`. Modal's default allocation when unset. |
| `memory` | Memory requested for the sandbox, e.g. `"2GB"`. Modal's default allocation when unset. |
| `gpu` | Modal GPU type, e.g. `"A100"`, `"H100"`, `"T4"`. |
| `region` | Modal region (e.g. `"us-east"`). Enterprise/Team plans. |
| `cloud` | Cloud provider (e.g. `"aws"`, `"gcp"`). Enterprise/Team plans. |
| `modal_environment` | Modal environment used for the App lookup. |

`ModalSandboxConfig` additionally holds the component-level fields set at registration time: `app_name` (the Modal App that hosts the Sessions) and the optional `token_id` / `token_secret` pair for explicit Modal credentials (otherwise Modal's ambient auth from `modal setup` is used).

Sandbox resources are configured only via `ModalSandboxSettings` (`cpu`, `memory`, `gpu` type string, `region`, `cloud`); cpu/memory follow Modal's defaults when unset. The step's `ResourceSettings` are intentionally **not** mirrored into the sandbox: the orchestrator already provisions those resources for the step itself, and the sandbox would double them. Example:

```python
from zenml import step
from zenml.integrations.modal.flavors import ModalSandboxSettings

@step(
    settings={
        "sandbox.modal": ModalSandboxSettings(gpu="A100", timeout=900),
    },
)
def agent_step(...): ...
```

Sandbox stdout/stderr automatically lands on the active step under a dedicated `sandbox:<session_id>` log source — see the [base sandbox docs](README.md#sandbox-logs) for the format. The `sandbox.<id>.dashboard_url` step-metadata entry is rendered as a clickable link to the Modal sandbox.

### Using it from a step

```python
from zenml import step
from zenml.client import Client


@step
def agent_step(prompt: str) -> str:
    sandbox = Client().active_stack.sandbox
    session = sandbox.create_session()
    try:
        process = session.exec(["python", "-c", "print(2 + 2)"])
        out = "".join(process.stdout())
        process.wait()
        return out
    finally:
        session.destroy()
```

Call `session.destroy()` when you're done, or the sandbox keeps billing until the `timeout` TTL kicks in as the backstop. Use `with sandbox.create_session() as session:` (which only calls `close()`, keeping the sandbox alive for a later `attach()`) when you *want* the sandbox to outlive the handle — but don't combine it with `destroy()`: if `destroy()` fails, it deliberately leaves the handle open for a retry, and the `with` block's exit would close it anyway.

### Snapshots and restore

Modal supports **filesystem-only** snapshots (`sandbox.snapshot_filesystem()`). Memory and live process state are not captured.

```python
from zenml import save_artifact, load_artifact

snap = session.create_snapshot()              # SandboxSnapshot
save_artifact(snap, name="agent_checkpoint")

# later — possibly in a different pipeline run:
snap = load_artifact("agent_checkpoint")
session = stack.sandbox.restore(snap)         # boots a new Sandbox from the stored Image
```

If your agent needs to preserve in-memory state across runs, prefer [`attach()`](README.md#snapshots-restore-and-attach) (reconnect to a still-live Session by id) over `restore()` (which boots a fresh Session every time).

### Caveats

- Modal sandbox env vars remain **readable from inside the Session** by any code the agent runs. The [Sandbox Auth Proxy pattern](README.md#security-considerations) is on the roadmap; until it lands, treat sandbox env as agent-visible.
- `session.close()` invalidates the local handle (further use raises `SandboxSessionClosedError`) but does **not** stop the Modal Sandbox — it keeps running until `session.destroy()` or the `timeout` TTL. Use `sandbox.attach(session_id)` for a fresh handle.
- `process.kill()` terminates the **whole Sandbox**, not just the one command — Modal exposes no per-command kill.
- `restore()` always returns a **new** Sandbox with a new id. The original `id` is unaffected; if you need id stability across runs, use `attach()` with a persisted session id instead.
