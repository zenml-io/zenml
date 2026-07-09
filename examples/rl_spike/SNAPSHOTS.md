# Sandbox filesystem snapshots (task F1, 2026-07-09)

*"What did the sandbox look like when this rollout failed?" The motivating
incident is [`BREAKAGE_LOG.md`](BREAKAGE_LOG.md) entry 16: hours of artifact
archaeology to learn that "reward 0.0" meant "the node had no disk." A
filesystem snapshot taken at failure time would have answered that in one
look. This document is the F1 deliverable: the flavor support matrix, how
the example wires snapshots in, and the gap list for core.*

## Support matrix (fact-checked against source, 2026-07-09)

The core API exists and is clean: `SandboxSession.create_snapshot()` returns
a `SandboxSnapshot` (component UUID + flavor-specific `ref` + free-form
metadata), and `BaseSandbox.restore(snapshot)` boots a fresh session from
it. Both default to `NotImplementedError`; flavors opt in.

| Flavor | `create_snapshot()` | `restore()` | What destroy erases | Notes |
|---|---|---|---|---|
| **Modal** | ✅ | ✅ | whole sandbox VM | The only implementation. `ref` = Modal Image id from `snapshot_filesystem()`. Introduced in PR #4867. |
| **Kubernetes** | ❌ | ❌ | whole pod (`delete_pod`) | Falls through to `NotImplementedError`. Documented as a known limitation (`docs/book/component-guide/sandboxes/kubernetes.md`). |
| **local** | ❌ | ❌ | workdir (`shutil.rmtree`) | Same — documented ❌ in `docs/book/component-guide/sandboxes/local.md`. |

In-flight work: PR #4870 (open) adds a *fourth* flavor — GKE Agent
Sandbox — whose description promises snapshot/restore via GKE Pod
Snapshots in a follow-up PR. Nothing in flight adds snapshots to the plain
Kubernetes flavor, which is the one this RL workload actually runs on.

## How restore actually works (Modal, the only implementation)

A snapshot is nothing but a Modal Image id plus the UUID of the ZenML
sandbox component that made it. `restore()`:

1. Refuses snapshots from a different component
   (`snapshot.sandbox_id != self.id` → `ValueError`), so the episode
   record must carry the component id — it does, inside the snapshot dict.
2. Rehydrates the Image by id and calls a plain `modal.Sandbox.create()`
   with it. This is **not** a resume: no processes survive, env vars are
   re-injected from the component's *current* settings, and cpu/gpu/TTL
   come from current settings too, not from snapshot time.
3. Nothing anywhere guarantees the Image still exists on Modal — there is
   no TTL/GC contract in the ZenML code; a vanished image surfaces as a
   `RuntimeError` at restore time.

There is also no idle/quiescence requirement in the code path: snapshots
can be taken mid-session, right after a failed scorer run — exactly what
`run_episode` does.

## What this example wires in

- `run.py --snapshot-on-failure` → pipeline param → broadcast to every
  mapped episode step (a plain bool in `.map()` rides along unchanged).
- `run_episode(..., snapshot_on_failure=True)`: when the episode fails —
  either the infra path raises (upload/exec/scorer crash, the entry-16
  case) or the scorer reports `error` on the generated pipeline — the
  session is snapshotted **inside** the `with` block, because
  `destroy_on_exit=True` erases the filesystem the moment the block exits.
  The result lands on the episode record (`snapshot` /
  `snapshot_error`) and in step metadata (`snapshot_ref`).
- Snapshotting is best-effort by construction: on the Kubernetes and local
  flavors every failing episode records
  `snapshot_error: "unsupported: ..."` and the run proceeds unchanged. The
  support gap is visible in the data instead of crashing the harness.
- `restore_sandbox.py <episode-artifact-version-id>`: loads the episode
  dict, rebuilds the exact sandbox component by the UUID inside the
  snapshot, restores, and gives you an exec prompt (or `--command` for
  one-shot). Unit tests: `tests/test_snapshot.py`.

## The by-hand restore demo (verified 2026-07-09)

Run on the `rl-spike-modal` stack (registered on staging: same components
as `rl-spike-local` but with the `modal_zenml_io` sandbox component —
ambient auth, app `rl-spike`, Modal workspace `zenml-io`, environment
`dev`, so sandboxes and snapshot images are visible in the shared Modal
dashboard; Michael's `modal` component works too but lives in his
personal workspace). The component's default image is bare
`python:3.11-slim` — no zenml — which accidentally reproduced entry 16's
exact signature: a canned PERFECT completion scored **reward 0.0, error
"import failed"**. Is that bad model code or a broken environment? The
old answer was hours of archaeology. The new answer:

```console
$ python restore_sandbox.py 137e6f7f-2fcc-4a18-abdc-dc72c1b0d215 \
    --command "cat pipeline.py; python -c 'import zenml'"
Restoring snapshot im-01KX3B9VEGQDE78S3VZMY55W2A via sandbox 'modal_zenml_io' (modal)...
Session sb-xE1MMepvwHVC7envgh3ey2 restored.
from zenml import step, pipeline

@step
def make_seven() -> int:
    return 7
...                                  # <- perfectly valid program
ModuleNotFoundError: No module named 'zenml'   # <- the environment is the culprit
Restored sandbox destroyed.
```

One command, from the failed episode's artifact id to the verdict: the
model's code was fine, the sandbox image couldn't import zenml.

Bonus finding from the same demo (entry 18): the first Modal attempt
died *before* upload because `upload_file(local, "pipeline.py")` with a
relative path — which the kubernetes flavor has accepted all spike long —
is an `InvalidError` on Modal. The session filesystem API has no workdir
contract; the example now falls back to its base64-over-exec transport on
any upload/download failure, since exec cwd is the only cross-flavor
anchor for relative paths.

## Gap list for core (the escalation outcome)

0. **No workdir contract on the session filesystem API** (entry 18,
   found during this task): `upload_file` with a relative remote path
   works on kubernetes, raises `NotImplementedError` on local, and is an
   `InvalidError` on Modal. Define what a relative path means, or reject
   relative paths uniformly at the base class.

1. **The flavor mismatch is the finding.** Snapshots exist only on Modal,
   but the long-running, wide fan-out workloads that *need* failure
   forensics (this spike: 280 episode pods per iteration) run on the
   Kubernetes flavor, where entry 16 happened and where snapshot support
   is documented-absent with no roadmap (PR #4870 targets a different,
   GKE-only flavor). A K8s implementation has honest options — commit the
   pod's filesystem to an image, or just tar the workdir to the artifact
   store — and even the tar option would have answered entry 16 in one
   click.
2. **Snapshots are invisible to lineage.** `SandboxSnapshot` is a plain
   pydantic model; unless user code (like ours) stuffs it into an episode
   record, nothing about a run says "this failed step left a snapshot."
   A first-class hook — snapshot ref as step metadata, the way session
   ids already are — would make the dashboard the entry point for
   forensics.
3. **No lifetime contract.** Modal snapshot images have no stated
   TTL/GC semantics; a snapshot ref saved in an episode record may or may
   not be restorable next week. Even "snapshots live N days" in the
   flavor docs would let harness authors set expectations.
4. **Restore uses current settings, silently.** If the component's image
   or resources changed since capture, the restored sandbox differs from
   the failed one in ways that don't announce themselves. Recording the
   resolved settings into `snapshot.metadata` at capture time (the field
   exists and is unused) would make drift at least diagnosable.
