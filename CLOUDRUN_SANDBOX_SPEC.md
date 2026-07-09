# Spec: Google Cloud Run Sandbox integration

Add a `cloudrun` sandbox flavor to the existing GCP integration, backed by
[Cloud Run sandboxes](https://docs.cloud.google.com/run/docs/code-execution)
(public preview, July 2026).

## 1. Background

### 1.1 What Cloud Run sandboxes are

Cloud Run sandboxes provide fast (<500 ms), strongly isolated environments for
executing untrusted code — LLM/agent-generated code being the headline use
case. Unlike Vercel/Cloudflare/Modal sandboxes there is **no standalone REST
API**: sandboxes are created *inside* a Cloud Run service instance that was
deployed with the sandbox launcher enabled:

```bash
gcloud beta run deploy SERVICE --image IMAGE_URL --sandbox-launcher
```

Inside such an instance a CLI at `/usr/local/gcp/bin/sandbox` is the control
surface:

| Command | Purpose |
|---|---|
| `sandbox do -- CMD` | ephemeral sandbox: create, run, destroy |
| `sandbox run <id> [CMD] --detach` | create a persistent sandbox |
| `sandbox exec <id> CMD [-e K=V] [-w DIR]` | run a command in a persistent sandbox |
| `sandbox delete <id> [--force]` | destroy a sandbox |
| `sandbox tar <id> --file F` | export the writable overlay as a tarball |
| `sandbox fork <src> <dst>` | clone a running sandbox |

Key flags: `--env`, `--mount type=bind,source=…,destination=…`, `--write`,
`--allow-egress` (no egress by default), `--import-tar`/`--export-tar`,
`--rootfs`, `--workdir`. Sandboxes share the host instance's CPU/memory and
see the instance's filesystem read-only (plus a writable tmpfs overlay).

### 1.2 What ZenML's sandbox abstraction expects

`src/zenml/sandboxes/` (on `develop`) defines the `SANDBOX` stack component
type:

- `BaseSandbox.create_session(settings, destroy_on_exit=False) -> SandboxSession`
  (required), `attach(session_id)` and `restore(snapshot)` (optional).
- `SandboxSession` hooks: `_exec` (required), `_close` (required),
  `_upload_file` / `_download_file` / `_create_snapshot` / `_destroy` /
  `_get_dashboard_url` (optional).
- `SandboxProcess`: `stdout()` / `stderr()` line iterators, `wait(timeout)`,
  `kill()`, `exit_code`; `collect()` is provided by the base class.
- `SandboxSnapshot(sandbox_id: UUID, ref: str, metadata: dict)`.

Reference implementations: `local`, `modal` (only flavor with snapshots),
`kubernetes`, and `cloudflare` (branch `feature/sandbox-cloudflare`, PR #4907)
which established the **bridge pattern**: a small HTTP service deployed on the
provider mediates between the ZenML client and the provider-local sandbox
primitive. Cloud Run's launcher architecture forces the same pattern.

## 2. Design

### 2.1 Architecture

```
ZenML client (step code)                     Google Cloud
┌──────────────────────────┐   HTTPS + ID    ┌──────────────────────────────┐
│ CloudRunSandbox          │   token (IAM)   │ Cloud Run service            │
│  └ CloudRunSandboxSession├────────────────►│ "sandbox bridge"             │
│     └ CloudRunSandbox-   │   SSE streams   │  (--sandbox-launcher)        │
│        Process           │◄────────────────┤  ┌────────┐  ┌────────┐      │
└──────────────────────────┘                 │  │sandbox1│  │sandbox2│ ...  │
                                             │  └────────┘  └────────┘      │
                                             └───────────┬──────────────────┘
                                                         │ snapshots (tar)
                                                         ▼
                                                    GCS bucket (optional)
```

The user deploys the provided **bridge service** (a small synchronous Python
HTTP server that shells out to the `sandbox` CLI) to Cloud Run with
`--sandbox-launcher`. The ZenML `cloudrun` sandbox component talks to it over
HTTPS, authenticating with Google-signed **ID tokens** (standard Cloud Run
IAM invoker auth) minted from the component's Google credentials.

The bridge speaks the **same wire protocol v1 as the Cloudflare bridge**
(`POST /v1/sandbox`, `POST /v1/sandbox/:id/exec` streaming SSE frames
`stdout`/`stderr` (base64) + `exit`/`error`, `PUT|GET /v1/sandbox/:id/file/*`,
`GET /v1/sandbox/:id/running`, `DELETE /v1/sandbox/:id`), with two
Cloud-Run-specific extensions:

1. **Per-exec env**: exec body accepts `"env": {K: V}` (the `sandbox` CLI
   supports `-e` natively), removing the Cloudflare limitation where per-exec
   env raises `NotImplementedError`. Session-level `sandbox_environment` is
   merged into every exec by the client — no bridge-side session objects.
2. **Snapshots**: `POST /v1/sandbox/:id/snapshot {"gcs_uri": "gs://…"}` runs
   `sandbox tar` and uploads the tarball to GCS; `POST /v1/sandbox` accepts
   `"import_tar_uri": "gs://…"` to boot from a snapshot. This gives Cloud Run
   parity with Modal (`create_snapshot`/`restore`), which Cloudflare lacks.

### 2.2 Deployment constraints (documented, not enforced)

- Persistent sandboxes are **instance-local**. The bridge must be deployed
  with `--max-instances 1` (or session affinity for advanced setups) so
  `exec` calls for a sandbox land on the instance that owns it.
- `--no-cpu-throttling` and `--min-instances 1` keep detached sandboxes alive
  between requests; otherwise Cloud Run may throttle/scale-to-zero and kill
  them.
- Cloud Run request timeout caps a single SSE exec stream at 60 min; the
  per-exec `timeout_ms` setting must stay below the service timeout.
- Sandbox CPU/memory come out of the bridge instance's allocation — size the
  service accordingly.

### 2.3 Placement: extend the `gcp` integration

The GCP integration already ships six flavors and depends on
`google-cloud-run` and `google-cloud-storage`; the flavor rides on the
existing `GoogleCredentialsConfigMixin`/`GoogleCredentialsMixin` (service
connector → SA key file → ADC) and the `gcp` service connector
(`resource_type="gcp-generic"`). Flavor name: **`cloudrun`** (precedent:
Vertex components use the service name `vertex`, not `gcp`).

### 2.4 New classes

`src/zenml/integrations/gcp/flavors/cloudrun_sandbox_flavor.py` (no google
imports — flavor files must import without the integration installed):

```python
class CloudRunSandboxSettings(BaseSandboxSettings):
    timeout_ms: int = 120_000        # per-exec cap, passed to the bridge
    cwd: Optional[str] = None        # default workdir inside the sandbox
    allow_egress: bool = False       # sandbox outbound network (CR default: off)

class CloudRunSandboxConfig(
    BaseSandboxConfig, GoogleCredentialsConfigMixin, CloudRunSandboxSettings
):
    service_url: str                       # https URL of the bridge service
    audience: Optional[str] = None         # ID-token audience; default service_url
    allow_unauthenticated: bool = False    # skip ID tokens (public bridge; discouraged)
    snapshot_uri_prefix: Optional[str] = None  # gs://bucket/prefix enabling snapshots
    # + project / service_account_path from GoogleCredentialsConfigMixin
    is_remote -> True

class CloudRunSandboxFlavor(BaseSandboxFlavor):
    name = "cloudrun"  # GCP_CLOUDRUN_SANDBOX_FLAVOR
    service_connector_requirements = ServiceConnectorRequirements(
        connector_type=GCP_CONNECTOR_TYPE, resource_type=GCP_RESOURCE_TYPE
    )
```

`service_url` gets the same https-or-localhost validator as the Cloudflare
`worker_url`.

`src/zenml/integrations/gcp/sandboxes/cloudrun_sandbox.py` (google imports
allowed here):

- `_CloudRunBridgeClient` — httpx wrapper (httpx is a core dependency),
  adapted from `_CloudflareBridgeClient`: same retry policy (idempotent
  methods only; 429/502/503/504), same SSE parsing, plus `env` on exec,
  `import_tar_uri` on create, and a `snapshot(sandbox_id, gcs_uri)` call.
  Auth is a pluggable header callback instead of a static bearer token.
- `CloudRunSandboxProcess` — SSE demux into stdout/stderr line buffers on a
  pump thread (same design as `CloudflareSandboxProcess`).
- `CloudRunSandboxSession` — implements `_exec` (with per-exec env support),
  `_upload_file`, `_download_file`, `_close`, `_destroy`, `_create_snapshot`
  (only when `snapshot_uri_prefix` is configured; `ref` = the GCS tarball URI).
- `CloudRunSandbox(BaseSandbox, GoogleCredentialsMixin)` — implements
  `create_session` (threading `destroy_on_exit`, per develop's signature),
  `attach`, and `restore` (creates a sandbox with `import_tar_uri=snapshot.ref`
  after `_validate_snapshot`).

**ID-token minting** (`_get_id_token_credentials`): start from
`self._get_authentication()` (mixin), then:

1. `service_account.Credentials` → `service_account.IDTokenCredentials`
   (same signer, `target_audience=audience`).
2. `impersonated_credentials.Credentials` →
   `impersonated_credentials.IDTokenCredentials(..., include_email=True)`.
3. Otherwise (plain ADC) → `google.oauth2.id_token.fetch_id_token`.
4. Failure → actionable error naming the three supported paths.

Tokens are cached and refreshed via `google.auth.transport.requests.Request`
before expiry; the bearer header is injected per request.

### 2.5 Bridge service (deployable example)

Following the Cloudflare precedent the bridge is not part of the `zenml`
package. It ships as `examples/cloudrun_sandbox_bridge/`:

- `main.py` — synchronous stdlib/`ThreadingHTTPServer` implementation of the
  wire protocol, shelling out to `/usr/local/gcp/bin/sandbox`:
  - create → `sandbox run <id> --detach [--allow-egress] [--import-tar …]
    --mount type=bind,source=/tmp/zenml-share/<id>,destination=/mnt/zenml
    --write -- sleep infinity` (the bind mount backs file transfer)
  - exec → `sandbox exec <id> -e K=V … -w CWD -- argv…`, stdout/stderr piped
    and re-emitted as base64 SSE frames, exit code in the `exit` frame
  - file PUT/GET → write/read `/tmp/zenml-share/<id>/…` on the host plus a
    `cp` exec inside the sandbox
  - snapshot → `sandbox tar <id> --file /tmp/….tar` then GCS upload
    (`google-cloud-storage`)
- `Dockerfile` + `README.md` with the exact deploy command:

  ```bash
  gcloud beta run deploy zenml-sandbox-bridge --source . \
    --sandbox-launcher --no-allow-unauthenticated \
    --max-instances 1 --min-instances 1 --no-cpu-throttling
  ```

The client treats the bridge URL as opaque, so users can substitute their own
implementation of the protocol.

### 2.6 Registration & metadata

- `src/zenml/integrations/gcp/__init__.py`: add
  `GCP_CLOUDRUN_SANDBOX_FLAVOR = "cloudrun"`; register
  `CloudRunSandboxFlavor` in `flavors()`.
- `src/zenml/integrations/gcp/flavors/__init__.py`: export config + flavor.
- Logo: `https://public-flavor-logos.s3.eu-central-1.amazonaws.com/sandbox/cloudrun.png`
  (asset upload tracked outside this repo, same as other new flavors).

## 3. Testing

`tests/unit/integrations/gcp/sandboxes/test_cloudrun_sandbox.py`, mirroring
the Cloudflare suite (`httpx.MockTransport`, no real bridge):

- flavor metadata / config validation (https enforcement, snapshot prefix
  validation)
- bridge client: create/delete/running/exec/file/snapshot request shapes,
  retry policy, error surfacing
- SSE parsing: interleaved stdout/stderr, exit frames, error frames,
  truncated streams
- process demux: concurrent stdout/stderr draining, `wait` timeout, `kill`
- session lifecycle: per-exec env merging, `destroy_on_exit`, closed-handle
  errors, upload/download size guards
- sandbox: `create_session`/`attach`/`restore` wiring, snapshot gating on
  `snapshot_uri_prefix`, ID-token path selection (mocked google.auth)

Live end-to-end testing against a real deployed bridge is manual, per the
repo's policy for external-service integrations.

## 4. Documentation

- `docs/book/component-guide/sandboxes/cloudrun.md` — deploy-the-bridge
  walkthrough, IAM setup (`roles/run.invoker` for the caller;
  GCS access for the bridge SA when snapshots are enabled), registration:

  ```bash
  zenml sandbox register my_cloudrun_sandbox --flavor cloudrun \
    --service_url=https://zenml-sandbox-bridge-….run.app
  zenml stack update my_stack --sandbox my_cloudrun_sandbox
  ```

- Add the page to `docs/book/component-guide/toc.md` under Sandboxes.

## 5. Out of scope (future work)

- `sandbox fork` → no abstraction hook today (a `fork()` on `SandboxSession`
  would benefit Modal too).
- Auto-deploying the bridge from the client via `google-cloud-run` (the
  Deployer already owns "deploy a Cloud Run service"; a convenience CLI could
  reuse it).
- Multi-instance bridges with session affinity routing.
- `aexec` async execution.

## 6. Risks

- **Preview API**: the `sandbox` CLI is pre-GA; flags may change. The CLI
  surface is isolated in the bridge (one file), not in the ZenML package.
- **Instance lifetime**: Cloud Run may recycle the bridge instance, killing
  persistent sandboxes. `attach()` reports this cleanly via
  `GET /running`; docs recommend snapshot checkpointing for long-lived state.
- **Protocol drift** with the Cloudflare bridge: mitigated by versioned
  paths (`/v1/…`) and per-flavor unit suites.
