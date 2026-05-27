# Sandbox Stack Component — PR #1: Core abstraction

Branch: `feature/sandbox-component-core`. Targets `develop`.

This document is the running plan + design rationale for the Sandbox stack component. It will become the PR description. Sections:

1. [Summary](#summary)
2. [Glossary](#glossary)
3. [API](#api)
4. [Config & Settings](#config--settings)
5. [PR #1 scope](#pr-1-scope)
6. [Out of scope / future PRs](#out-of-scope--future-prs)
7. [ADR 0001 — Sandbox is a step's tool, not a step launcher](#adr-0001--sandbox-is-a-steps-tool-not-a-step-launcher)
8. [ADR 0002 — Attach and Restore as separate verbs](#adr-0002--attach-and-restore-as-separate-verbs)
9. [Running task list](#running-task-list)

---

## Summary

Adds a new ZenML stack component type, **Sandbox**, that lets a step (typically running an AI agent) execute LLM-generated code in an isolated environment (Modal container, E2B microVM, k8s pod, etc.) and stream results back. The step *consumes* the sandbox via `Client().active_stack.sandbox`; the sandbox does not run the step. Multiple sandboxes per stack are allowed.

This PR ships the base abstraction plus one built-in flavor (`local`). Real-isolation flavors land in dedicated follow-up PRs from branches off this one:

- `feature/sandbox-modal` → Modal flavor (PR #4867; stacked)
- `feature/sandbox-pydantic-ai-example` → PydanticAI example (PR pending; stacked on Modal)
- `feature/sandbox-agent-substrate` → kubernetes-sigs/agent-sandbox (Agent Substrate) flavor — *not started*
- additional flavors (E2B, Daytona) cribbed from the abandoned `feature/sandboxes-stack-component` branch as we discover real demand

PR #1 (this branch) ships:
- The abstract `BaseSandbox`, `SandboxSession`, `SandboxProcess`, `BaseSandboxSnapshot` interfaces (with their optional methods raising `NotImplementedError` by default).
- The `SANDBOX` `StackComponentType` enum value (repeatable per stack) + `Stack.sandbox` / `Stack.sandboxes` properties + `--sandbox` CLI flag.
- `ZENML_ACTIVE_STEP_IMAGE` injected into the step environment by `BaseOrchestrator._inject_active_step_image_env` for containerized orchestrators so the `STEP_IMAGE` sentinel resolves.
- Base helpers: `_resolve_session_environment` (env+secret merge with `{{secret.key}}` resolution), `_validate_snapshot_provider`, `forward_session_logs` / `forward_lines` for log routing into ZenML's step log stream.
- **`LocalSandbox` flavor** — subprocess-based, built-in (no extra deps), registered in `FlavorRegistry.builtin_flavors`. **No isolation** — loud warning on every `create_session()` — but suitable for examples, unit tests, and development against the abstraction.
- 62 unit tests (37 base + 25 LocalSandbox).
- User docs: `docs/book/component-guide/sandboxes/{README.md, local.md}` + toc entry.

The outbound-credential proxy ("Sandbox Auth Proxy" pattern shipped by LangSmith, Vercel, Cloudflare) is **deferred to a later PR** once we've shipped concrete flavors and have real usage to model against.

---

## Glossary

### Sandbox

A **stack component** that provides isolated code execution to a step at runtime. The step *uses* the sandbox (via the active stack) — the sandbox does **not** run the step. Distinct from a Step Operator, which submits and executes the step itself.

Typical use: an AI agent running inside a ZenML step reaches for the active stack's Sandbox to execute generated code as a tool, possibly across many turns of an agent loop.

When prose says "the sandbox", the **Sandbox Session** (below) is almost always meant. Use "Sandbox component" or "Sandbox flavor" when referring to the stack-component entity.

### Sandbox Session

A **live, bounded interaction with a single isolated execution environment** (container / microVM / pod) created by a Sandbox component. Has an `id`, accepts many `exec` calls, can optionally be snapshotted, and is explicitly closed when done.

Created by `Sandbox.create_session()`. One Sandbox component can mint many Sessions.

### Sandbox Snapshot

A serializable, provider-specific reference to a captured Sandbox Session state. Round-trips: `session.snapshot() → BaseSandboxSnapshot`, then `sandbox.restore(snapshot) → SandboxSession`. Snapshots from one flavor cannot be restored by another.

**Restore** always returns a *new* Session (fresh `id`). The original Session is unaffected.

### Attach vs Restore

Two distinct ways to obtain a Session that isn't freshly created:

- **Attach** (`sandbox.attach(session_id)`) — reconnect to an **already-live** Session by id. No snapshot needed. Use for subagent / cross-pipeline flows that want to share one live Session.
- **Restore** (`sandbox.restore(snapshot)`) — materialize a new Session from a stored Snapshot. The original Session may or may not still exist; restore doesn't care.

### Session Environment

The base image and environment variables a Session is created with.

**Component-level (no new fields on `BaseSandboxConfig`).** Every `StackComponent` already exposes `self.environment: Dict[str, str]` and `self.secrets: List[UUID]` ([docs](https://docs.zenml.io/concepts/environment-variables#configuring-environment-variables-on-stack-components)). Sandbox flavors read those at `create_session()` time — explicit env vars from `self.environment` plus secrets resolved via `Client().get_secret(uuid).secret_values` and exploded into env vars.

**Per-step (`BaseSandboxSettings`):**

- `base_image: Union[str, None]` — `None` → flavor default; sentinel `STEP_IMAGE` → image the current ZenML step is running in (warns and falls back to flavor default if not containerized); any other string → exact image URI.
- `environment: Dict[str, str]` — per-step overrides merged onto `StackComponent.environment` (Settings wins on key collision). Values may use ZenML `{{secret.key}}` references; auto-resolved at access time.
- `copy_local_env: bool` (default `False`) — propagate the step process's *full* local env (incl. resolved secrets) into the Session. Convenience for prototyping; off by default for security.
- `forward_logs_to_step: Optional[bool]` (default `None`) — see "Log forwarding" below.

LLM-generated code running inside the Session can read everything in this environment. The mitigation pattern (auth-injecting proxy) is future work; see *Out of scope*.

---

## API

```python
# src/zenml/sandboxes/base_sandbox.py

STEP_IMAGE = "<step>"  # sentinel for "use the step's runtime image"


class SandboxProcess(ABC):
    """Handle to a running command inside a Session."""
    @abstractmethod
    def stdout(self) -> Iterator[str]: ...   # line-delimited, utf-8 decoded
    @abstractmethod
    def stderr(self) -> Iterator[str]: ...
    @abstractmethod
    def wait(self, timeout: Optional[float] = None) -> int: ...
    @abstractmethod
    def kill(self) -> None: ...
    @property
    @abstractmethod
    def exit_code(self) -> Optional[int]: ...


class BaseSandboxSnapshot(BaseModel):
    provider: str        # must match a flavor name
    ref: str             # provider-specific (Modal image id, etc.)
    metadata: Dict[str, Any] = {}


class SandboxSession(ABC):
    id: str

    @abstractmethod
    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess: ...

    async def aexec(self, command, *, cwd=None, env=None) -> SandboxProcess:
        raise NotImplementedError(...)

    def snapshot(self) -> BaseSandboxSnapshot:
        raise NotImplementedError(...)

    def upload_file(self, local_path: str, remote_path: str) -> None:
        raise NotImplementedError(...)

    def download_file(self, remote_path: str, local_path: str) -> None:
        raise NotImplementedError(...)

    @abstractmethod
    def close(self) -> None:
        """Release the local handle. Sandbox keeps running on the provider."""

    def destroy(self) -> None:
        """Terminate the sandbox on the provider. Invalidates the session id."""
        raise NotImplementedError(...)

    # __enter__ / __exit__ → close()


class BaseSandbox(StackComponent, ABC):
    @abstractmethod
    def create_session(
        self, settings: Optional["BaseSandboxSettings"] = None
    ) -> SandboxSession: ...

    def attach(self, session_id: str) -> SandboxSession:
        """Reconnect to an already-live Session by id. Cheap."""
        raise NotImplementedError(...)

    def restore(self, snapshot: BaseSandboxSnapshot) -> SandboxSession:
        """Materialize a new Session from a stored Snapshot."""
        # Base validates snapshot.provider == self.flavor; subclasses
        # super().restore(snap) first, then do their work.
        raise NotImplementedError(...)


class BaseSandboxFlavor(Flavor):
    @property
    def type(self) -> StackComponentType:
        return StackComponentType.SANDBOX

    @property
    def config_class(self) -> Type[BaseSandboxConfig]:
        return BaseSandboxConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseSandbox]: ...
```

`exec()` raises `SandboxExecError` (subclass of `RuntimeError`) synchronously if the launch itself fails (binary not found, image broken). Once a `SandboxProcess` is returned, runtime errors flow through `exit_code`/`stderr()`.

---

## Config & Settings

```python
class BaseSandboxConfig(StackComponentConfig):
    # No fields. Env vars and secrets live on StackComponent (self.environment,
    # self.secrets) — set via `zenml stack-component register --env ... --secret ...`.
    pass


class BaseSandboxSettings(BaseSettings):
    base_image: Optional[str] = None       # None | STEP_IMAGE | "image:tag"
    environment: Dict[str, str] = {}       # MERGED onto StackComponent.environment; Settings wins
    copy_local_env: bool = False
    timeout_seconds: Optional[int] = None
    forward_logs_to_step: Optional[bool] = None   # see "Log forwarding"
```

Merge order at `create_session()`:
1. `StackComponent.environment` (component-level defaults).
2. Each `StackComponent.secrets` UUID resolved via `Client().get_secret(uuid).secret_values` and exploded into env vars.
3. `Settings.environment` overrides on key collision.
4. If `Settings.copy_local_env=True`, the step's local env is layered last.

**Log forwarding.** When effective `forward_logs_to_step` is `True`, the flavor opens a ZenML `LoggingContext` with `source=f"sandbox:{session_id}"` so sandbox stdout/stderr surfaces in the UI as a distinct log stream per session — `zenml.utils.logging_utils.setup_logging_context(source=...)` is the wiring point.

Flavor-side default resolution (when the user leaves `forward_logs_to_step=None`): `True` if `base_image == STEP_IMAGE` (the sandbox is running the step's own image and is "integrated"), `False` for the flavor's default image or any custom image (sandbox is "alien" — don't presume the user wants their logs intermingled).

Implementation notes:
- Before forwarding, check `is_step_logging_enabled(step_configuration, pipeline_configuration)` — if the user disabled step logs globally (`ZENML_DISABLE_STEP_LOGS_STORAGE=1` or via pipeline/step config), the sandbox path must also silently no-op.
- `setup_logging_context` requires a reachable log store. The default `ArtifactLogStore` writes through the stack's `artifact_store` (already a required stack component). For non-pipeline / script-mode usage where no `LoggingContext` is available, wrap the setup call in try/except and fall back to plain `logger.info()` line-by-line.

Multi-per-stack: `StackComponentType.SANDBOX.supports_multiple_per_stack == True`. `active_stack.sandbox` returns the default (first attached); `active_stack.sandboxes` returns `Dict[str, BaseSandbox]`.

---

## PR #1 scope

| File | Purpose |
|---|---|
| `src/zenml/enums.py` | Add `SANDBOX = "sandbox"`; include in `supports_multiple_per_stack` set. |
| `src/zenml/sandboxes/__init__.py` | Re-exports for both base classes and the `LocalSandbox` flavor. |
| `src/zenml/sandboxes/base_sandbox.py` | All base classes + `STEP_IMAGE` sentinel + `SandboxExecError` + base helpers (`_resolve_session_environment`, `_validate_snapshot_provider`, `forward_session_logs`, `forward_lines`, `resolve_forward_logs_to_step`). |
| `src/zenml/sandboxes/local_sandbox.py` | Built-in `LocalSandbox` flavor — subprocess-based, no isolation, loud warning on each `create_session()`. |
| `src/zenml/stack/stack.py` | Add `sandbox` / `sandboxes` properties on `Stack`. Update `__init__` to accept sandbox(es). |
| `src/zenml/stack/flavor_registry.py` | Register `LocalSandboxFlavor` in `builtin_flavors`. |
| `src/zenml/cli/stack.py` | `--sandbox` / `-sb` repeatable flag on `zenml stack register/update`. |
| `src/zenml/orchestrators/base_orchestrator.py` | `_inject_active_step_image_env` helper exports `ZENML_ACTIVE_STEP_IMAGE` for containerized orchestrators so the `STEP_IMAGE` sentinel resolves. |
| `tests/unit/sandboxes/test_base_sandbox.py` | 37 tests: NotImplementedError defaults, `_validate_snapshot_provider`, snapshot Pydantic round-trip, env-merge order, log-forwarding helpers. |
| `tests/unit/sandboxes/test_local_sandbox.py` | 25 tests: exec lifecycle, env merge, workdir cleanup, settings coercion, builtin-flavor registration. |
| `tests/unit/orchestrators/test_base_orchestrator.py` | 3 new tests: `_inject_active_step_image_env` for containerized vs non-containerized orchestrators + failure-swallowing. |
| `docs/book/component-guide/sandboxes/{README.md,local.md}` | User-facing overview + Local flavor docs. |
| `docs/book/component-guide/toc.md` | Add sandbox entry + Local sub-entry. |

**Branching strategy.** Concrete flavors live on branches off this one (`feature/sandbox-modal` is open as PR #4867; `feature/sandbox-pydantic-ai-example` stacked on top of Modal). Each branch opens its own PR. If PR #1 merges first, the flavor PRs rebase onto `develop`. While #4866 is open, downstream PRs show its commits too — GitHub auto-prunes once the base merges.

---

## Out of scope / future PRs

**Modal flavor (PR #4867, branch `feature/sandbox-modal`)** — already open. `src/zenml/integrations/modal/sandboxes/` + flavor + materializer for `ModalSandboxSnapshot` (Modal Image ref). Maps to `modal.Sandbox.create / exec / snapshot_filesystem / from_id`. Implements log forwarding via the base `forward_session_logs` helper. 41 unit tests.

**PydanticAI example (PR pending, branch `feature/sandbox-pydantic-ai-example`)** — open after Modal lands. Demonstrates an agent using `SandboxSession.exec` as its `run_python` tool. Works against any flavor; defaults to LocalSandbox for the quickstart.

**Agent Substrate flavor (branch: `feature/sandbox-agent-substrate`)** — *not started*. `src/zenml/integrations/agent_sandbox/` against `agents.x-k8s.io/v1alpha1` `Sandbox` CRD; not GKE-specific.

**Sandbox Auth Proxy.** Industry-standard pattern shipped by LangSmith, Vercel, Cloudflare. Routes outbound HTTP from the Session through a sidecar/paired-sandbox proxy that injects `Authorization` headers per host-pattern rule, so LLM-generated code never sees raw credentials. Reference design: kami-agent's mitmproxy-addon implementation. Config schema sketch:

```python
class SandboxProxyRule(BaseModel):
    name: str
    match_hosts: List[str]
    inject_headers: Dict[str, str]   # values support {{secret.key}}
```

Each flavor implements proxy infra (Modal: paired sandbox running mitmdump; k8s: sidecar container + NetworkPolicy; E2B/Daytona: custom template). Lands once at least one flavor is in to model against. Until then, secrets injected through `StackComponent.environment` / `secrets` are readable by LLM-generated code — documented in `docs/book/component-guide/sandboxes/README.md`.

**Later flavors.** E2B, Daytona — lift from the abandoned `feature/sandboxes-stack-component` branch as demand emerges (cost-tracking metadata, structured logging via `forward_sandbox_output`, etc.).

**Other deferred items:**
- Auto-explode `secrets: List[str]` field (sugar for "expand every key of these secrets as env vars"). Adopt if real usage demands it.
- Async-first interface (currently `aexec` is opt-in NotImpl-by-default).
- "Lazy" helper module (`zenml.sandboxes.get_session()` context manager) — design considered, deferred.

---

## ADR 0001 — Sandbox is a step's tool, not a step launcher

**Status**: Accepted

### Context

ZenML already has several stack components that "run code somewhere": Orchestrator runs pipelines; Step Operator runs individual steps remotely; Image Builder + Container Registry prepare the env. The Sandbox is adjacent to all of these, and the framing decision is foundational. Three framings:

- **(A)** A backend the step *consumes* during its own execution.
- **(B)** A launcher that *runs* the step on the user's behalf.
- **(C)** A non-stack-component library.

### Decision

**(A).** The Sandbox is a stack component the step uses, accessed via `Client().active_stack.sandbox` from inside the step body. The Sandbox does not run the step. A step running on (say) SageMaker step operator can still grab the active stack's Sandbox and use it as a tool. Closest analogs: Experiment Tracker, Alerter — ambient capabilities the step reaches for.

### Consequences

- Interface centers on `BaseSandbox.create_session() -> SandboxSession`, not `submit(step, ...)`. No step-operator lifecycle on the component.
- Sessions are long-lived, stateful, multi-`exec` — fits an agent's tool-use loop.
- Composes orthogonally with Step Operators.
- Multi-per-stack consistent with Step Operator / Alerter / Experiment Tracker.

### Alternatives considered

- **(B) Step-operator framing** — rejected. Steps are atomic; sandboxes are interactive. A step operator cannot model `exec` driven by an agent loop inside the step.
- **(C) Library, not stack component** — rejected. Loses ZenML's secret resolution (`{{secret.key}}`), settings/config plumbing, swap-by-stack ergonomics.

---

## ADR 0002 — Attach and Restore as separate verbs

**Status**: Accepted

### Context

A Sandbox Session is the live execution environment. There are two legitimate ways a caller might want to obtain a Session that isn't freshly created:

1. **Reconnect to a still-live Session by id.** Common in subagent / cross-pipeline flows. Every backend supports lookup by id (Modal `Sandbox.from_id`, E2B `Sandbox.connect`, Daytona `get`, k8s CR lookup).
2. **Materialize a new Session from a stored snapshot.** Provider semantics diverge sharply (Modal: FS-only image; E2B: full pause/resume; Daytona: none; Agent Substrate: gVisor checkpoint).

A single overloaded method (`restore(snap_or_id, reuse=...)`) conflates two contracts — one needs a `BaseSandboxSnapshot`, the other a plain string; one presupposes someone took a snapshot, the other does not.

### Decision

Two distinct methods on `BaseSandbox`:

```python
def attach(self, session_id: str) -> SandboxSession: ...        # NotImpl default
def restore(self, snapshot: BaseSandboxSnapshot) -> SandboxSession: ...  # NotImpl default
```

`restore` always returns a *new* Session with a new id, even when the backend reuses memory state. Uniform contract across flavors.

### Consequences

- Subagent flow does not require a snapshot. Parent `save_artifact(session.id)`; child `sandbox.attach(get_artifact(...))`.
- Snapshot remains opt-in per flavor; Daytona implements `attach` only.
- Framework does not auto-close Sessions on step exit (close/destroy split on `SandboxSession`). Required for `attach` to be useful across step boundaries.

### Alternatives considered

- **Single overloaded `restore(snap_or_id, reuse=True)`** — rejected. Hides the semantic split behind a flag.
- **Only `restore`, fake snapshot for reconnect** — rejected. Forces snapshot ceremony for the common path.
- **Only `attach`, drop `restore`** — rejected. Loses snapshot/replay/branching use case.

---

## Running task list

| # | Task | Status |
|---|------|--------|
| 1 | Create branch off develop | ✅ done |
| 2 | Add `SANDBOX` to `StackComponentType` enum + multi-per-stack set | ✅ done |
| 3 | Create `src/zenml/sandboxes/` with base classes | ✅ done |
| 4 | Wire `SANDBOX` into `Stack` (singular `.sandbox` + plural `.sandboxes`) | ✅ done |
| 5 | ~~Implement Modal flavor~~ → moved to `feature/sandbox-modal` (PR #4867) | dropped from PR #1 |
| 6 | Unit tests for base abstraction | ✅ done (37 tests) |
| 7 | Two rounds of review fixes (Michael + Stefan) | ✅ done |
| 8 | CLI `--sandbox` / `-sb` flag + `ZENML_ACTIVE_STEP_IMAGE` orchestrator wiring | ✅ done |
| 9 | `LocalSandbox` built-in flavor (subprocess; no isolation; for examples + tests) | ✅ done (25 tests) |
| 10 | Docs overview page + Local flavor page + `toc.md` entry | ✅ done |
| 11 | `bash scripts/format.sh`, lint clean, PR #4866 open and reviewed twice | ✅ done |
