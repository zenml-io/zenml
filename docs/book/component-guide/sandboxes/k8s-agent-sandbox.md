---
description: Running agent code in Kubernetes Agent Sandbox pods.
---

# Kubernetes Agent Sandbox

The Kubernetes Agent Sandbox flavor wraps the [`kubernetes-sigs/agent-sandbox`](https://github.com/kubernetes-sigs/agent-sandbox) operator and its `k8s-agent-sandbox` Python SDK in ZenML's [Sandbox](README.md) interface. Each session claims a sandbox pod on your cluster (from a `SandboxTemplate` custom resource), and the agent inside a step can `exec()` commands against it without leaving ZenML.

### When to use it

Use the Kubernetes Agent Sandbox flavor when:

- You already run workloads on Kubernetes and want sandboxes co-located with the rest of your infrastructure.
- You need full pod-level control (node selectors, tolerations, volumes, GPUs) over the sandbox environment.
- You want sandbox auth handled by the same ZenML service connector as your other Kubernetes components.

### How to deploy it

1. Install the `agent-sandbox` operator and its CRDs on your cluster (see the [operator docs](https://github.com/kubernetes-sigs/agent-sandbox)).
2. Make sure the identity you use (kubeconfig or service connector) can `get` / `list` / `create` / `delete` `sandboxtemplates` and `sandboxclaims` in `extensions.agents.x-k8s.io`.
3. Install the ZenML integration:
   ```bash
   zenml integration install k8s_agent_sandbox
   ```

### How to register the component

```bash
zenml sandbox register my-k8s-sandbox \
    --flavor=k8s_agent_sandbox \
    --namespace=agent-workloads \
    --image=ghcr.io/my-org/sandbox-runtime@sha256:...

# Optionally authenticate via a service connector that exposes a
# kubernetes-cluster resource (gcp or kubernetes connector):
zenml sandbox connect my-k8s-sandbox --connector my-k8s-connector

zenml stack update --sandbox my-k8s-sandbox
```

Without a connector, the flavor falls back to the ambient kubeconfig (`~/.kube/config` or `KUBECONFIG`). With a connector, fresh short-lived credentials are fetched on every `create_session()` call.

### Template mode vs inline mode

The flavor creates sandboxes from a `SandboxTemplate` custom resource, in one of two modes:

- **Template mode** (recommended for production): set `template_name` to a pre-created `SandboxTemplate` in the cluster. The referenced template's spec wins; `image`, `pod_settings`, and `sandbox_environment` are ignored.
- **Inline mode** (convenient for prototyping): leave `template_name` unset. The flavor synthesizes a short-lived `SandboxTemplate` per session from `image`, `sandbox_environment`, and `pod_settings`, and deletes it again on `close()` / `destroy()`. The image MUST contain the agent-sandbox runtime exposing the sandbox HTTP API on port 8888.

### Settings reference

`K8sAgentSandboxSettings` (override on individual `@step` decorations) and the equivalents as component-level defaults on `K8sAgentSandboxConfig`:

| Field | Purpose |
|---|---|
| `image` | Container image for inline mode. No default — inline mode refuses to run without an explicit image. Pin to a digest or stable tag. |
| `template_name` | Name of a pre-created `SandboxTemplate`. Setting it switches to template mode. |
| `namespace` | Kubernetes namespace for the sandbox claim (must already exist). |
| `sandbox_ready_timeout` | Seconds to wait for the sandbox pod to become Ready. |
| `pod_settings` | Full `KubernetesPodSettings` surface (node selectors, tolerations, volumes, resources, ...). Inline mode only. |
| `sandbox_environment` | Env vars injected into the synthesized template's container. Inline mode only — in template mode, bake env into the template or pass per-exec `env`. |

Component-level only (on `K8sAgentSandboxConfig`): `connection_mode` (`gateway` recommended for production, `local_tunnel` for local dev, `direct` + `api_url`, or `in_cluster`), `gateway_name`, and `gateway_namespace`.

Sandbox pod resources (cpu / memory / gpu) are sized exclusively via `pod_settings.resources` — the step's own `ResourceSettings` are not applied to the sandbox pod:

```python
from zenml import step
from zenml.integrations.k8s_agent_sandbox.flavors import (
    K8sAgentSandboxSettings,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

@step(
    settings={
        "sandbox.k8s_agent_sandbox": K8sAgentSandboxSettings(
            image="ghcr.io/my-org/sandbox-runtime@sha256:...",
            pod_settings=KubernetesPodSettings(
                resources={"requests": {"cpu": "2", "memory": "4Gi"}},
            ),
        ),
    },
)
def agent_step(...): ...
```

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

### Caveats

- The SDK's `commands.run` is a single blocking HTTP POST — `exec()` returns only after the command has exited, and `stdout()` / `stderr()` replay the captured output. There is no live streaming.
- Snapshots, `restore()`, and `attach()` are not supported by this flavor.
- `session.close()` does **not** terminate the sandbox pod, and the operator has no built-in TTL on a claim — call `session.destroy()` (or clean up cluster-side) when you're done, or the pod keeps running.
- When the step itself runs inside the cluster, the SDK prefers the in-cluster service account over connector credentials — grant that service account the required RBAC instead of relying on the connector.
- Service-connector tokens are short-lived (e.g. ~1h on GKE). Each `create_session()` fetches fresh credentials, but a session that outlives its token will see 401s — open a fresh session in that case.
