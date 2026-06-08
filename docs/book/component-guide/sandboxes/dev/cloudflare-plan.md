# Cloudflare Sandbox flavor — implementation plan

Branch: `feature/sandbox-cloudflare` (off `feature/sandbox-component-core`).
Reference: Modal flavor on `feature/sandbox-modal` (mirrored structurally).

## Scope (and what's NOT in scope)

- **In scope (v1)**: Cloudflare Sandbox flavor backed by the bridge HTTP API.
  Create/exec/file/snapshot/restore/destroy, log routing through
  `LoggingContext`, SSE stream parsing.
- **Out of scope (v1)**:
  - PTY/WebSocket support — the bridge exposes it (`GET /v1/sandbox/:id/pty`)
    but the ZenML `SandboxSession` contract doesn't need it.
  - Sandbox→external credential injection (Cloudflare's outbound proxy /
    secure-binding pattern). Document as future seam.
  - Cloudflare service connector consumption — connector is being built in
    parallel on a sibling branch; we'll merge it in later. For now, all auth
    is via stack-component config (`worker_url` + `api_key` SecretField).
  - GPU knobs — Cloudflare Sandboxes don't expose GPU.

## Verified facts (from sources, not memory)

### Current `BaseSandbox` interface (post-schustmi)

Read directly from `src/zenml/sandboxes/{base,session,process,snapshot}.py`:

| Abstract | Signature |
|---|---|
| `BaseSandbox.create_session(settings)` | `→ SandboxSession` |
| `SandboxSession.exec(command, *, cwd, env)` | `→ SandboxProcess` |
| `SandboxSession.close()` | `→ None` |
| `SandboxProcess.stdout()/stderr()` | `→ Iterator[str]` |
| `SandboxProcess.wait(timeout)` | `→ int` |
| `SandboxProcess.kill()` | `→ None` |
| `SandboxProcess.exit_code` | `→ Optional[int]` |
| `BaseSandboxFlavor.implementation_class` | `→ Type[BaseSandbox]` |

Default-raises (we opt in by overriding):
`attach`, `restore`, `aexec`, `create_snapshot`, `upload_file`,
`download_file`, `destroy`.

`SandboxSession.__init__(*, id, parent)` — assign session-specific state
BEFORE calling `super().__init__()` because base `__init__` calls
`_publish_sandbox_metadata` which calls `_get_dashboard_url` (subclass hook).

`SandboxProcess.__init__(session, started_at)` — both mandatory.

`SandboxSnapshot` — `sandbox_id: UUID`, `ref: str`, `metadata: Dict[str, Any]`.
No subclassing needed; we return plain `SandboxSnapshot` (per the schustmi-era
audit verdict applied to Modal).

`BaseSandbox._validate_snapshot(snapshot)` validates `snapshot.sandbox_id == self.id`
(component identity, not flavor name).

### Cloudflare bridge HTTP API (from
[developers.cloudflare.com/sandbox/bridge/http-api](https://developers.cloudflare.com/sandbox/bridge/http-api/))

**Auth**: `Authorization: Bearer <SANDBOX_API_KEY>` on every `/v1/sandbox/*` route.

**Sandbox lifecycle**:
- `POST /v1/sandbox` → `{"id": "<sandbox-id>"}` (no request body documented)
- `DELETE /v1/sandbox/:id` → 204
- `GET /v1/sandbox/:id/running` → `{"running": bool}`

**Exec** (`POST /v1/sandbox/:id/exec`):
- Body: `{"argv": [...], "timeout_ms": <ms>, "cwd": "<path>"}`
- Response: `text/event-stream` with:
  - `event: stdout`, data = base64 chunk
  - `event: stderr`, data = base64 chunk
  - `event: exit`, data = `{"exit_code": N}`
  - `event: error`, data = `{"error": "...", "code": "..."}`

**Files** (paths confined to `/workspace`):
- `PUT /v1/sandbox/:id/file/*` — raw bytes (max 32 MiB)
- `GET /v1/sandbox/:id/file/*` — raw bytes back

**Snapshots** (workspace persistence):
- `POST /v1/sandbox/:id/persist[?excludes=...]` → raw tar bytes
- `POST /v1/sandbox/:id/hydrate` (body: tar bytes, max 32 MiB) → ok

**Sessions** (within a sandbox; scope cwd + env):
- `POST /v1/sandbox/:id/session` → `{"id": "<session-id>"}`
- `DELETE /v1/sandbox/:id/session/:sid` → 204
- Subsequent `/exec`, `/file/*`, `/pty` pass `Session-Id: <sid>` header

**Bucket mounts** (R2 / S3-compat): `POST /v1/sandbox/:id/mount`,
`POST /v1/sandbox/:id/unmount`. Pulling in v1 if cheap; otherwise v1.1.

**Warm pool**: `GET /v1/pool/stats`, `POST /v1/pool/prime`. Documented as
behavior we benefit from automatically; no client wiring needed.

### Mapping decisions

**ZenML SandboxSession ↔ Cloudflare bridge sandbox** (not bridge session). One
bridge sandbox per ZenML session. The Cloudflare bridge's *session* concept
(scoping cwd/env) is an implementation detail we hide: each ZenML `SandboxSession`
optionally creates a bridge session at construction to carry the per-session env.

**Why hide bridge sessions?** Adding a second hierarchy level into ZenML's
API would force users to think about which level their env lives at. Single
ZenML session = single bridge sandbox = (optionally) a single bridge session
keeps the mental model identical to Modal.

**Env injection path**:
1. On `create_session(settings)`: resolve `eff.sandbox_environment`, then
   `POST /v1/sandbox` to get sandbox_id, then `POST /v1/sandbox/:id/session`
   if `eff.sandbox_environment` is non-empty (passing the env there if the
   API accepts it — open question 1).
2. On `exec(..., env=...)`: per-exec env. Bridge exec body doesn't document
   an `env` field. Mirror the k8s flavor's approach: prepend
   `KEY=value KEY2=value2 ...` to argv (with `env` binary) when the bridge
   doesn't accept per-exec env natively. Verify against bridge OpenAPI.

## File layout

Mirror Modal's structure:

```
src/zenml/integrations/cloudflare/
  __init__.py                        # ZenML integration + flavor registration
  flavors/
    __init__.py                      # re-exports CloudflareSandboxFlavor*
    cloudflare_sandbox_flavor.py     # Settings/Config/Flavor
  sandboxes/
    __init__.py                      # re-exports CloudflareSandbox
    cloudflare_sandbox.py            # bridge HTTP client + Process/Session/Sandbox

tests/unit/integrations/cloudflare/
  __init__.py
  sandboxes/
    __init__.py
    test_cloudflare_sandbox.py       # ~25 tests mirroring test_modal_sandbox.py

docs/book/component-guide/sandboxes/
  cloudflare.md                      # docs page mirroring modal.md
```

## Class layout — concrete contract

### `cloudflare_sandbox_flavor.py`

```python
CLOUDFLARE_SANDBOX_FLAVOR = "cloudflare"
CLOUDFLARE_STEP_IMAGE_SENTINEL = "<step>"

class CloudflareSandboxSettings(BaseSandboxSettings):
    base_image: Optional[str]   # registry URI | "<step>" | None (→ default_image)
    timeout_ms: Optional[int]   # per-exec timeout; bridge default if None
    cwd: Optional[str]          # default working directory inside /workspace

class CloudflareSandboxConfig(BaseSandboxConfig, CloudflareSandboxSettings):
    # Auth — both as SecretFields so they go through the secrets store
    worker_url: str             # bridge worker URL
    api_key: Optional[str] = SecretField(default=None)
    default_image: str          # fallback when base_image is None or sentinel unresolved
    # NO is_remote override — wins via MRO when needed; defaults to False
    # which is wrong for Cloudflare → must override to True

class CloudflareSandboxFlavor(BaseSandboxFlavor):
    name = "cloudflare"
    logo_url = "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/sandbox/cloudflare.png"
    config_class = CloudflareSandboxConfig
    implementation_class → lazy import CloudflareSandbox
```

Decision: `is_remote = True`. Override on Config (the StackComponentConfig
default is False; Cloudflare needs True). The Modal flavor used to have this
explicit override; after we deleted it there, it inherits True via
ModalStepOperatorConfig. We don't have a parent here (no Cloudflare step
operator yet), so we keep the explicit override.

### `cloudflare_sandbox.py`

```python
class CloudflareBridgeClient:
    """Thin wrapper over httpx.Client for the bridge HTTP API."""
    # Holds the worker_url + bearer token, builds requests, handles SSE.
    # Single shared httpx.Client lives on the CloudflareSandbox component
    # for connection pooling. Sessions hold a reference.

class CloudflareSandboxProcess(SandboxProcess):
    # Streams the SSE response from /v1/sandbox/:id/exec.
    # Parses event: stdout|stderr|exit|error; base64-decodes data chunks.
    # Buffers chunks into lines (mirror Modal's _line_buffer helper).
    # exit_code captured when event=exit arrives; wait() blocks until then.

class CloudflareSandboxSession(SandboxSession):
    # Owns: sandbox_id, optional bridge_session_id, bridge client reference.
    # exec → POST /exec (with Session-Id header if bridge_session_id is set).
    # upload_file / download_file → PUT/GET /file/*, stream in 1 MiB chunks
    #   (bridge max body is 32 MiB; warn or error if file exceeds).
    # create_snapshot → POST /persist; ref = "tar:<sha256>" cached server-side
    #   (open question 4: does the bridge cache the tar, or do we have to
    #   re-upload? See below).
    # close → no-op (sandbox keeps running on Cloudflare; logging cleanup
    #   centralized in base __exit__).
    # destroy → DELETE /v1/sandbox/:id. Idempotent.
    # _get_dashboard_url → None for now (no public dashboard link from a
    #   bridge sandbox id; the bridge worker is the user's own Worker).

class CloudflareSandbox(BaseSandbox):
    # _bridge_client: lazy-cached httpx.Client, thread-locked.
    # create_session(settings) → resolve settings + env, POST /v1/sandbox,
    #   optionally POST /v1/sandbox/:id/session for env, return CloudflareSandboxSession.
    # attach(session_id) → reconnect to existing sandbox; GET /running to
    #   verify it's still up; return Session.
    # restore(snapshot) → validate, POST /v1/sandbox, then POST /hydrate with
    #   the tar bytes pulled from snapshot.ref (where the tar is stored is
    #   open question 4).

def _resolve_step_image() -> Optional[str]:
    # Mirror Modal: look up the active step's containerized-orchestrator image.
    # Same code, factored to a helper so both flavors stay in lockstep.
```

## Open questions (resolve before / during implementation)

1. **Does `POST /v1/sandbox` accept env in the request body, or do we need
   the bridge-session detour?** The HTTP-API doc shows no request body for the
   sandbox creation endpoint. The OpenAPI schema at `/v1/openapi.json` will
   answer authoritatively. If sandbox creation doesn't accept env, we either
   (a) create a bridge session + scope env there, or (b) inline `KEY=VAL` into
   argv for every exec. Plan: prefer (a) for cleanliness; fall back to (b)
   only if bridge sessions don't accept env either. Will verify at impl time
   by hitting the live OpenAPI schema on a deployed bridge.

2. **Per-exec env on `/v1/sandbox/:id/exec`?** Doc shows `{argv, timeout_ms, cwd}`
   only. Same OpenAPI verification. If unsupported, prepend `env KEY=VAL ...`
   to argv (k8s flavor pattern).

3. **Bridge OpenAPI schema gives us the source of truth.** Plan: during
   implementation, fetch the JSON schema once from a working bridge and
   reference it inline in the relevant docstrings.

4. **Snapshot storage**: `POST /persist` returns tar bytes (the bridge does
   NOT store the tar; we get raw bytes back). So we hold them in `snapshot.ref`?
   That's wrong — `ref` is a `str`, not bytes; and a 32-MiB tar shouldn't
   ride in a model field. Decision: the snapshot tar is materialized as a
   first-class **ZenML artifact** (via a small `CloudflareSandboxSnapshot`
   materializer that pickles the tar bytes), and `snapshot.ref` becomes the
   artifact id or an artifact-store URI. Mirror how Modal returns just the
   Image id but Cloudflare's "id" is the tar content itself.
   - Alternative: skip snapshot support in v1 (raise NotImplementedError);
     `restore` similarly. Snapshot artifact ergonomics need a more thought-out
     design and isn't a v1 critical path. **Lean toward skipping for v1.**

5. **`Session-Id` header propagation**: if we create a bridge session for env
   scoping, we MUST send `Session-Id` on every exec/file call. The bridge
   client must thread this through cleanly. Plan: ZenML session holds an
   optional `bridge_session_id` attribute; client methods take it as a kwarg.

6. **Connector consumption seam**: when the Cloudflare service connector
   lands, the consumption point is `worker_url` + `api_key`. We accept both
   as fields today; later, when a connector is linked, the component's
   `connector_credentials` would override them. **Don't pre-build the
   integration** — leave the seam by reading auth via `self.config.worker_url`
   / `self.config.api_key`. When the connector arrives, the cloudflare
   integration registers a resource type that hands those two values out,
   and we add a thin `_resolve_auth()` indirection on `CloudflareSandbox`
   that prefers connector creds when present.

## Auth model (verbatim from the task brief, restated for the docs page)

Three boundaries, distinct mechanisms:

1. **ZenML → bridge** (we own): `Authorization: Bearer <api_key>` on every
   request. Stored as `SecretField` on the config — never as plaintext
   config or env var. Travels through ZenML's secrets store like any other
   stack-component secret.
2. **Bridge → Cloudflare account** (not our problem; mention in docs): the
   bridge Worker's own binding to the account, established at deploy time.
   We never see account-level keys.
3. **Sandbox → external** (future seam): Cloudflare's outbound proxy /
   binding model for credential injection. Documented seam, not v1.

## Test coverage (mirror Modal's `test_modal_sandbox.py` shape)

About 20–25 unit tests, organized into classes:

- `TestFlavorMetadata` — name/type/logo_url/config_class/implementation_class
- `TestConfigDefaults` — base_image None default, is_remote True, fields exist
- `TestAuth` — `api_key` is a SecretField; bearer-token header on every call
- `TestSettingsMerge` — component defaults survive partial override, etc.
- `TestSession` — `_publish_sandbox_metadata` called, dashboard URL handling
- `TestExec` — argv shape, cwd, env merge, SSE parse (stdout/stderr/exit/error),
  base64 decode, launch failure → `SandboxExecError`
- `TestFileOps` — upload PUT, download GET, large-file chunking
- `TestSnapshot` — skipped if we punt v1, OR validate provider mismatch raises
- `TestStepImageResolution` — `<step>` sentinel resolves via `_resolve_step_image`,
  fallback to `default_image`
- `TestLifecycle` — close is no-op, destroy DELETEs, attach reconnects

All tests use a mocked bridge HTTP layer (responses.mock-style or httpx
MockTransport). No live Cloudflare.

## Out-of-scope / future work (documented in plan but NOT coded)

- PTY/WebSocket exec mode
- Sandbox→external credential injection (Cloudflare outbound proxy)
- Cloudflare Service Connector consumption (drops in once the connector branch lands)
- R2 bucket mounts (`POST /v1/sandbox/:id/mount`) — useful but not gating v1
- Cloudflare durable-objects-based session warm-up beyond what the bridge's
  warm pool gives us automatically

## Order of work

1. Stub `src/zenml/integrations/cloudflare/` package + integration registration.
2. Implement `CloudflareBridgeClient` (httpx wrapper, bearer header, SSE parser).
3. Implement `CloudflareSandboxProcess` (consume SSE, line-buffer, exit-code capture).
4. Implement `CloudflareSandboxSession` (exec, file ops, close, destroy).
5. Implement `CloudflareSandbox` (create_session, attach; defer snapshot/restore for v1).
6. Tests in lockstep with each piece.
7. Docs page + toc entry.
8. Pre-commit: ruff format + ruff check, AST parse, smoke import.

Estimated PR delta: ~800–1000 LoC code + ~600 LoC tests + ~150 LoC docs.
Comparable to PR #4867 (Modal flavor) at landing time.
