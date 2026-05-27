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
    --app_name=my-agent-app \
    --default_image=python:3.11-slim
```

Add env vars and ZenML-stored secrets that should land in every Session at the standard component level — see the [Environment Variables docs](https://docs.zenml.io/concepts/environment-variables#configuring-environment-variables-on-stack-components):

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

`ModalSandboxSettings` (override on individual `@step` decorations) and the equivalents as component-level defaults on `ModalSandboxConfig`:

| Field | Purpose |
|---|---|
| `base_image` | `None` → component `default_image`; `STEP_IMAGE` sentinel → image the current ZenML step is running in; any other string → exact image URI for `modal.Image.from_registry`. |
| `environment` | Per-step env vars merged onto `StackComponent.environment` (Settings wins on collision). |
| `copy_local_env` | If `True`, propagate the step process's full local env into the Session. Off by default. |
| `timeout_seconds` | Forwarded to Modal's `Sandbox.create(timeout=)`. |
| `gpu` | Modal GPU spec, e.g. `"A100"`, `"H100"`, `"T4"`. |
| `cpu` | Cores requested. |
| `memory_mb` | Memory in MiB. |
| `region` | Modal region (e.g. `"us-east"`). Enterprise/Team plans. |
| `cloud` | Cloud provider (e.g. `"aws"`, `"gcp"`). Enterprise/Team plans. |
| `forward_logs_to_step` | Auto-route Sandbox stdout/stderr into ZenML step logs as a per-session log source tagged with the session id (visible as a separate stream in the UI). Active when the Session is used as a context manager (`with sandbox.create_session() as session:`). Default: `True` when `base_image == STEP_IMAGE`, else `False`. |

### Using it from a step

```python
from zenml import step
from zenml.client import Client


@step
def agent_step(prompt: str) -> str:
    sandbox = Client().active_stack.sandbox
    with sandbox.create_session() as session:
        process = session.exec(["python", "-c", "print(2 + 2)"])
        out = "".join(process.stdout())
        process.wait()
        return out
```

### Snapshots and restore

Modal supports **filesystem-only** snapshots (`sandbox.snapshot_filesystem()`). Memory and live process state are not captured.

```python
from zenml import save_artifact, load_artifact

snap = session.snapshot()                     # ModalSandboxSnapshot
save_artifact(snap, name="agent_checkpoint")  # uses the dedicated materializer

# later — possibly in a different pipeline run:
snap = load_artifact("agent_checkpoint")
session = stack.sandbox.restore(snap)         # boots a new Sandbox from the stored Image
```

If your agent needs to preserve in-memory state across runs, prefer [`attach()`](README.md#snapshots-restore-and-attach) (reconnect to a still-live Session by id) over `restore()` (which boots a fresh Session every time).

### Caveats

- Modal sandbox env vars are passed as a `modal.Secret`, but they remain **readable from inside the Session** by any code the agent runs. The [Sandbox Auth Proxy pattern](README.md#security-considerations) is on the roadmap; until it lands, treat sandbox env as agent-visible.
- `session.close()` is a no-op (Modal Sandbox is a stateless client handle); use `session.destroy()` to force-terminate, or let Modal's `timeout` expire.
- `restore()` always returns a **new** Sandbox with a new id. The original `id` is unaffected; if you need id stability across runs, use `attach()` with a persisted session id instead.
