---
description: Pod-backed sandbox sessions for isolated command execution on Kubernetes.
---

# Kubernetes Sandbox

The Kubernetes sandbox flavor creates one Kubernetes pod per sandbox session and executes each `session.exec(...)` command inside that pod using Kubernetes `exec`.

## How to register

```bash
zenml integration install kubernetes
zenml sandbox register k8s-sb --flavor=kubernetes --connector=<CONNECTOR_NAME>
zenml stack update --sandbox k8s-sb
```

The [Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/service-connectors-guide) must provide access to a Kubernetes cluster. Alternatively, you can register the sandbox without a connector:

```bash
zenml sandbox register k8s-sb --flavor=kubernetes --kubernetes_context=<CONTEXT_NAME>
```

In this case, the sandbox uses your local kubeconfig credentials. `kubernetes_context` selects the kubeconfig context to use and defaults to the active one.

## Additional configuration

Some configuration options for the Kubernetes sandbox can only be set through the sandbox config when you register it (and cannot be changed per-session through the settings):

- **`incluster`** (default: False): If `True`, the sandbox will load the in-cluster Kubernetes configuration and create session pods in the same cluster it is running in, ignoring the `kubernetes_context`.
- **`kubernetes_context`**: The name of the Kubernetes context to use for creating session pods (ignored if using a service connector or `incluster`).
- **`kubernetes_namespace`** (default: "zenml"): The Kubernetes namespace in which session pods are created. The namespace must already exist in the Kubernetes cluster.

The following configuration options can be set either through the sandbox config or overridden using `KubernetesSandboxSettings`:

- **`sandbox_environment`**: Environment variables to set in session pods and command executions.
- **`image`** (default: "python:3.11-slim"): The container image used for session pods. The image must provide `/bin/sh` and `base64`, so distroless images are not supported.
- **`pod_settings`**: Node selectors, labels, affinity, tolerations, secrets, environment variables, image pull secrets, the scheduler name and additional arguments to apply to the session pods. These can be either specified using the Kubernetes model objects or as dictionaries.
- **`service_account_name`**: The name of a Kubernetes service account to use for session pods. If not configured, pods use the namespace default service account.
- **`automount_service_account_token`** (default: False): If `True`, a Kubernetes API token is mounted into session pods, allowing code running in the sandbox to call the Kubernetes API with the service account's RBAC permissions.
- **`privileged`** (default: False): If the container should be run in privileged mode.
- **`owner`** (default: `none`): The Kubernetes object that owns session pods, so that they are garbage-collected together with it. See [Owning session pods](#owning-session-pods).
- **`pod_startup_timeout`** (default: 120): The maximum time (in seconds) to wait for a session pod to become running.
- **`api_request_timeout`**: Timeout (in seconds) for Kubernetes API requests. If not set, client defaults are used.

## Security model

This flavor is designed to make safer defaults possible, but cluster policy remains the primary security boundary.

### ZenML-side safeguards (default behavior)

- Service account token is not mounted in sandbox pods (`automount_service_account_token=False`).
- `sandbox_environment` values are visible to executed code. Do not inject secrets you do not want sandbox code to read.

For untrusted code, set `service_account_name` to a dedicated least-privilege service account instead of relying on the namespace default.

### Required cluster-admin controls

For untrusted LLM code, configure at least:

- **Least-privilege RBAC** for sandbox service accounts.
- **Pod Security Admission** (or equivalent policy engine) to forbid privileged containers and host namespace escapes.
- **Runtime hardening policy** (e.g. Kyverno/Gatekeeper) to enforce non-root, read-only root filesystem, seccomp, and no privilege escalation where required.
- **Network policies** with explicit egress/ingress rules (default-deny plus allow-list).
- **ResourceQuota / LimitRange** to constrain runaway compute and memory usage.
- **Image policy controls** (trusted registry, signature/provenance checks if available).

Without these controls, sandbox pods may still reach internal services or external networks based on cluster defaults.

## Feature set

| Feature | Kubernetes | Notes |
|---|---|---|
| `create_session()` | ✅ | Creates a pod and waits until it is running. |
| `exec()` | ✅ | Uses Kubernetes exec websocket streaming. |
| Streaming output | ✅ | Stdout/stderr stream line-by-line through `SandboxProcess`. |
| Sandbox log forwarding | ✅ | Output is forwarded into `sandbox:<session_id>` step logs. |
| `destroy()` | ✅ | Deletes the backing pod. |
| `attach(session_id)` | ✅ | Re-attaches to a running session pod. |
| `snapshot()` / `restore()` | ❌ | Not implemented. |
| `upload_file` / `download_file` | ✅ | Transfers file content through Kubernetes exec. Uploads are limited to 256 MiB per file. |

## Attaching to a running session

`attach(session_id)` re-creates a session handle for an existing session pod. Attaching fails if the pod does not exist, is not running, or was created by a different sandbox component.

{% hint style="warning" %}
An attached session shares the pod with the original session handle. Calling `destroy()` on either handle deletes the pod, after which `exec()` calls on the other handle fail.
{% endhint %}

## Owning session pods

A session pod is only deleted by `session.destroy()`. A step that dies abruptly before reaching it (for example because it was `OOMKilled`, evicted or its node was preempted) leaves its session pods running, even with `destroy_on_exit=True`.

To protect against that, set `owner` so that Kubernetes [garbage-collects](https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/) the session pod together with the step:

| `owner` | The session pod is deleted together with |
|---|---|
| `none` (default) | nothing, it lives until `session.destroy()` is called |
| `pod` | the pod running the step, so every retry of the step gets session pods of its own |
| `job` | the Kubernetes Job running the step pod, which also removes the session pods of all its retries |

```python
from zenml import step
from zenml.client import Client
from zenml.integrations.kubernetes.flavors import (
    KubernetesSandboxOwner,
    KubernetesSandboxSettings,
)


@step
def run_owned_sandbox() -> str:
    sandbox = Client().active_stack.sandbox
    with sandbox.create_session(
        settings=KubernetesSandboxSettings(owner=KubernetesSandboxOwner.JOB),
        destroy_on_exit=True,
    ) as session:
        return session.exec(["python", "--version"]).collect().stdout
```

Keep in mind:

- **The owner is deleted later than it fails.** Kubernetes removes the session pod when its owner object is *deleted* from the cluster, not when the step fails: a crashed step pod stays around in the `Failed` phase until its Job is cleaned up, for example after the `ttl_seconds_after_finished` of the orchestrator. An owner prevents session pods from leaking forever, it does not replace `destroy_on_exit=True`.
- **Same namespace only.** Owner references cannot cross namespaces, so the step must run on Kubernetes (e.g. with the [Kubernetes orchestrator](../orchestrators/kubernetes.md) or [step operator](../step-operators/kubernetes.md)) in the `kubernetes_namespace` of the sandbox. Otherwise, `create_session()` raises an error instead of creating an unowned pod.
- **The owner is set on creation.** The owner reference is part of the pod manifest, so the session pod is never left without an owner, not even while it is starting.

## Lifecycle behavior

- `close()` closes only the local session handle. It does not delete the pod.
- `destroy()` deletes the backing pod and then closes the handle.
- `kill()` only stops streaming output. Kubernetes exec does not propagate signals on disconnect, so the command keeps running inside the pod until the pod is deleted.

