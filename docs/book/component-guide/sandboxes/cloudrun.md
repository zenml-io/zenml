---
description: Running agent code in Google Cloud Run sandboxes.
---

# Google Cloud Run Sandbox

[Cloud Run sandboxes](https://docs.cloud.google.com/run/docs/code-execution) give you fast (sub-second), strongly isolated environments for executing untrusted code — most commonly code written by an LLM agent. The `cloudrun` sandbox flavor wraps them in ZenML's [Sandbox](README.md) interface, so an agent inside a step can `exec()` commands, stream output, transfer files, snapshot the filesystem to Cloud Storage, and restore from those snapshots.

### How it works

Cloud Run sandboxes have no standalone REST API: the `sandbox` CLI that creates and drives them only exists *inside* a Cloud Run service deployed with the sandbox launcher enabled. ZenML therefore talks to a small **bridge service** that you deploy once to Cloud Run — see [`examples/cloudrun_sandbox_bridge`](https://github.com/zenml-io/zenml/tree/main/examples/cloudrun_sandbox_bridge) — and authenticates to it with Google-signed ID tokens, the standard Cloud Run IAM invoker flow.

```
step code ──HTTPS + ID token──▶ bridge service (--sandbox-launcher) ──sandbox CLI──▶ isolated sandboxes
```

### When to use it

Use the Cloud Run sandbox flavor when:

- You're already running on Google Cloud and want sandbox isolation without adding another vendor.
- You need no-egress-by-default isolation for LLM-generated code (network access is opt-in per sandbox).
- You want filesystem snapshots stored durably in Cloud Storage that can boot new sandboxes.

### How to deploy it

1. Deploy the bridge service (from `examples/cloudrun_sandbox_bridge`):

   ```bash
   gcloud beta run deploy zenml-sandbox-bridge \
     --source . \
     --region europe-west1 \
     --sandbox-launcher \
     --no-allow-unauthenticated \
     --max-instances 1 --min-instances 1 --no-cpu-throttling
   ```

   `--max-instances 1` matters: persistent sandboxes live on a single instance, and a scaled-out bridge would route execs to instances that don't own the sandbox. `--min-instances 1 --no-cpu-throttling` keep detached sandboxes running between requests.

2. Grant the identity that runs your pipelines `roles/run.invoker` on the service. For snapshots, grant the *bridge's* runtime service account write access to your snapshot bucket.

3. Install the GCP integration:

   ```bash
   zenml integration install gcp
   ```

### How to register the component

```bash
zenml sandbox register cloudrun_sandbox \
    --flavor=cloudrun \
    --service_url=https://zenml-sandbox-bridge-abc123-ew.a.run.app \
    --snapshot_uri_prefix=gs://my-bucket/zenml-sandbox-snapshots

zenml stack update --sandbox cloudrun_sandbox
```

Authentication follows the usual GCP component rules: a linked [GCP Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector) takes priority, then `service_account_path`, then Application Default Credentials. Note that ID tokens (which Cloud Run IAM requires) can only be minted from service-account-based credentials — user credentials from `gcloud auth application-default login` won't work.

```bash
zenml service-connector register gcp_connector --type gcp --auth-method service-account \
    --service_account_json=@path/to/key.json
zenml sandbox connect cloudrun_sandbox --connector gcp_connector
```

### How to use it

```python
from zenml import step
from zenml.client import Client


@step
def run_agent_code(code: str) -> str:
    sandbox = Client().active_stack.sandbox
    with sandbox.create_session(destroy_on_exit=True) as session:
        session.upload_file("requirements.txt", "/tmp/requirements.txt")
        output = session.exec(["python3", "-c", code]).collect()
        if output.exit_code != 0:
            raise RuntimeError(output.stderr)
        return output.stdout
```

Snapshots capture the sandbox's writable filesystem overlay as a tarball in Cloud Storage and can seed new sandboxes — including after the original bridge instance is gone:

```python
snapshot = session.create_snapshot()          # -> tarball at snapshot_uri_prefix
...
restored = sandbox.restore(snapshot)          # new sandbox from the tarball
```

### Settings reference

`CloudRunSandboxSettings` (override on individual `@step` decorations):

| Field | Purpose |
|---|---|
| `sandbox_environment` | Env vars applied to every command in the session. Cloud Run sandboxes inherit nothing from the host, so anything the code needs must be set here (or per-exec via `session.exec(..., env=...)`). |
| `timeout_ms` | Per-exec timeout in milliseconds (default 120000). Must stay below the bridge service's Cloud Run request timeout. |
| `cwd` | Default working directory for commands. |
| `allow_egress` | Give sandboxes outbound network access (off by default). |

Config-only fields on the component: `service_url`, `audience`, `allow_unauthenticated`, `snapshot_uri_prefix`, plus the standard GCP `project` / `service_account_path`.

### Limitations

- Persistent sandboxes are **instance-local**: if Cloud Run recycles the bridge instance, running sandboxes are lost (`attach()` reports this cleanly). Snapshot anything you need to keep.
- File transfer through the bridge is capped at 32 MiB per request; move larger data through Cloud Storage.
- A single exec is bounded by the Cloud Run request timeout (max 60 minutes).
- Cloud Run sandboxes are in public preview; the underlying CLI may change.

For the full config surface, see the [SDK docs](https://sdkdocs.zenml.io).
