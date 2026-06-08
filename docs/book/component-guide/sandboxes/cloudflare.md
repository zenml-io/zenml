---
description: Running agent code in Cloudflare sandboxes.
---

# Cloudflare Sandbox

The Cloudflare Sandbox flavor wraps the [Cloudflare Sandbox bridge](https://developers.cloudflare.com/sandbox/) — a small Cloudflare Worker that fronts the Workers / Containers API — in ZenML's [Sandbox](README.md) interface, so an agent inside a step can `exec()` commands, stream stdout/stderr, upload and download files, and tear down the sandbox without leaving ZenML.

### When to use it

Use the Cloudflare Sandbox flavor when:

- You want ephemeral, isolated containers for running LLM-generated code with low cold-start latency on Cloudflare's edge.
- You already operate on Cloudflare and want to keep your sandbox infrastructure on the same provider as your [R2 artifact store](../artifact-stores/r2.md) or [Cloudflare container registry](../container-registries/cloudflare.md).
- You want a thin, HTTP-only surface — no Python SDK to install beyond ZenML itself.

### How to deploy the bridge

The Cloudflare Sandbox is fronted by a Worker (the "bridge") that you deploy into your own Cloudflare account. The bridge exposes the documented `/v1/sandbox/*` HTTP API; ZenML calls it from your pipeline.

1. Follow the Cloudflare [Sandbox deploy guide](https://developers.cloudflare.com/sandbox/) (or `npx wrangler deploy` from the official sandbox template) to install the bridge Worker into your account.
2. Pick a long, random string for the bridge's `SANDBOX_API_KEY` env binding. The Worker checks every request for `Authorization: Bearer <SANDBOX_API_KEY>`.
3. Note the deployed Worker URL (e.g. `https://sandbox-bridge.<account>.workers.dev`).

### How to register the component

```bash
zenml integration install cloudflare
zenml sandbox register my-cf-sandbox \
    --flavor=cloudflare \
    --worker_url=https://sandbox-bridge.your-account.workers.dev \
    --api_key=<your-SANDBOX_API_KEY>
```

Then attach it to your stack:

```bash
zenml stack update --sandbox my-cf-sandbox
```

### Authentication: three boundaries

The Cloudflare sandbox crosses three security boundaries; ZenML only owns the first one:

1. **ZenML → bridge** — the `api_key` configured on the flavor is sent as `Authorization: Bearer <token>` on every HTTP request to `<worker_url>/v1/sandbox/*`. It is stored as a ZenML secret.
2. **Bridge → Cloudflare account** — the bridge Worker holds its own Cloudflare service binding (configured at deploy time via Wrangler). ZenML never sees Cloudflare API tokens.
3. **Sandbox → external** — code running inside the sandbox can call external services through Cloudflare's outbound proxy. Auth for that path is the agent author's responsibility.

Because the bridge bearer token is scoped to a single Worker (not a whole Cloudflare account), it intentionally **does not** flow through the ZenML Cloudflare service connector — it lives directly on the sandbox flavor as a `SecretField`.

### Settings reference

`CloudflareSandboxSettings` (override per `@step`) and the equivalents on `CloudflareSandboxConfig` (component-level defaults):

| Field | Purpose |
|---|---|
| `worker_url` | Base URL of the deployed bridge Worker. Required. |
| `api_key` | Bearer token for the bridge. Stored as a ZenML secret. |
| `base_image` | Reserved for future use: the current bridge does not accept a custom image on `POST /v1/sandbox`. Pass `"<step>"` to request the active step's containerized-orchestrator image (still informational today). |
| `default_image` | Component-level fallback for `base_image`. |
| `timeout_ms` | Per-exec timeout in milliseconds. Passed to the bridge as `timeout_ms`. |
| `cwd` | Default working directory for execs inside the sandbox (server-side paths are confined to `/workspace`). |
| `sandbox_environment` | Env vars injected into the sandbox session. When set, ZenML asks the bridge to scope them to a session (`POST /v1/sandbox/:id/session`) and falls back to inlining `KEY=VAL` into argv if the bridge rejects the body shape. |

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

Sandbox stdout/stderr automatically lands on the active step under a dedicated `sandbox:<session_id>` log source — see the [base sandbox docs](README.md#sandbox-logs) for the format.

### Limitations (v1)

- **No snapshot / restore.** The bridge's `POST /persist` returns raw tar bytes rather than a server-side reference, which needs a materializer design we have deferred. Calling `create_snapshot()` / `restore()` raises `NotImplementedError`.
- **No R2 mount.** The bridge exposes `POST /v1/sandbox/:id/mount` but ZenML does not surface it yet.
- **No PTY / WebSocket support.** Outside `BaseSandbox`'s contract.
- **No GPU / region / cloud knobs.** Cloudflare does not expose those on the sandbox API.
- **`base_image` is informational.** The bridge does not currently accept a custom image on sandbox creation; the Worker's bound container image is used. The setting is recorded and surfaced in logs so you can roll forward when the bridge gains image overrides.
- **`kill()` is a no-op warn.** The bridge has no per-exec kill; call `session.destroy()` to terminate the whole sandbox.

### Related

- [Cloudflare service connector](../../how-to/auth-management/service-connectors-guide.md) — used by the [R2 artifact store](../artifact-stores/r2.md) and the [Cloudflare container registry](../container-registries/cloudflare.md). The sandbox flavor deliberately does **not** flow through the connector; see the three-boundary explanation above.
