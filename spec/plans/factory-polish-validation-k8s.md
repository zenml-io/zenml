# Fix edge cases in the software factory fix loop

## Root cause

In `examples/software_factory/pipeline.py`, the `software_factory` pipeline
runs a bounded `for attempt in range(max_fix_iterations):` loop
(`pipeline.py:401-432`) that assigns the local variables `tests` and
`verdict` only *inside* the loop body. After the loop, both variables are
read again to build the `deploy_approval` metadata (`pipeline.py:435-438`):

```python
pr_result = pr.load()
metadata = {"pr_url": pr_result.url, "tests": tests.load().model_dump()}
if verdict is not None:
    metadata["verdict"] = verdict.load().model_dump()
```

This produces two bugs:

1. **`max_fix_iterations=0` crashes.** `range(0)` never executes the loop
   body, so `tests` is never bound. `tests.load()` then raises
   `NameError: name 'tests' is not defined` when building the metadata.
   `verdict` is pre-initialized to `None` before the loop
   (`pipeline.py:400`), so it doesn't have this problem, but `tests` does
   not have an equivalent default.

2. **Stale test report when the loop is exhausted after a `fix`.** Every
   loop iteration either (a) ends in `break` right after an *approved*
   review, or (b) ends by calling `fix` (because tests failed, or tests
   passed but the review was not approved). If the loop runs out of
   `max_fix_iterations` without ever breaking, the very last thing that
   happened on the branch is a `fix` commit — but `tests` still holds the
   `TestReport` from *before* that final fix. The `deploy_approval` human
   task then shows a test report that doesn't reflect the current state of
   the branch, which is misleading for whoever approves the deploy.

Note that in Python, whether a `for` loop's `break` was hit is naturally
observable via the loop's `else` clause: the `else` block runs iff the loop
completed all iterations without hitting `break`. Since the only `break` in
this loop happens immediately after an approved review, "loop finished via
`else`" is exactly equivalent to "the last action taken was a `fix`" (this
also correctly covers `max_fix_iterations=0`, where the loop trivially
completes without breaking and no `fix` ever ran).

## Fix approach

Both edge cases can be closed with a small, self-contained change to the
`software_factory` function body — no changes to `models.py`,
`factory_utils.py`, or the individual `@step` functions are needed.

### 1. Validate `max_fix_iterations` up front

Add a guard at the very top of `software_factory` (before `write_plan` is
even invoked, so a bad value fails fast without spending any sandbox/agent
time):

```python
if max_fix_iterations < 1:
    raise ValueError(
        "max_fix_iterations must be at least 1 so the fix loop can run "
        "at least one test/review cycle."
    )
```

This directly resolves edge case 1 by rejecting `max_fix_iterations=0` (and
negative values) before the loop, so `tests` is always bound by the time the
`deploy_approval` metadata is built. This matches the issue's first
suggested option ("validate that `max_fix_iterations` is at least 1 and
raise a clear error") and is simpler/more explicit than making the metadata
construction tolerate missing `tests`/`verdict`, which would otherwise
silently produce an incomplete approval task.

### 2. Re-run tests after the loop if it ended on a `fix`

Use the `for...else` construct so the "loop exhausted without an approved
review" case is expressed directly, and run one more `run_tests` call there
with a distinct step id:

```python
verdict = None
for attempt in range(max_fix_iterations):
    tests = run_tests(
        workspace=workspace,
        repo=repo,
        branch=target_branch,
        test_command=test_command,
        id=f"run_tests_{attempt}",
    )
    verdict = None
    if tests.load().passed:
        verdict = review(
            workspace=workspace,
            repo=repo,
            branch=target_branch,
            issue=issue,
            plan=plan,
            tests=tests,
            base_branch=base_branch,
            id=f"review_{attempt}",
        )
        if verdict.load().approved:
            break
    pr = fix(
        workspace=workspace,
        repo=repo,
        branch=target_branch,
        issue=issue,
        tests=tests,
        base_branch=base_branch,
        verdict=verdict,
        id=f"fix_{attempt}",
    )
else:
    tests = run_tests(
        workspace=workspace,
        repo=repo,
        branch=target_branch,
        test_command=test_command,
        id="run_tests_final",
    )
```

Notes on why this is correct and minimal:

- The `else` block only runs when the `for` loop finishes without `break`,
  i.e. exactly when the last thing that happened was a `fix` (or when
  `max_fix_iterations` was validated to be `>= 1` but the loop still never
  approved — same condition). This matches the issue's requested behavior
  ("if the last action was a fix, run the tests one more time") without
  needing a separate boolean flag to track "did we break".
  This wording is used as-is in the docstring of `software_factory` if it
  needs updating, and in the README, if the README shows this snippet.
- The new step id `run_tests_final` is distinct from `run_tests_{attempt}`
  for every possible `attempt`, preserving the pipeline's deterministic,
  resumable step-id scheme (`README.md`, "Bounded fix loop with
  deterministic step ids").
- `verdict` is intentionally left untouched by the `else` block. It either
  stays `None` (last iteration's tests failed, so no review ran before that
  fix) or holds the last (non-approved) `ReviewVerdict` (last iteration's
  tests passed but review wasn't approved). Both are still accurate
  descriptions of "the last review feedback that triggered a fix" — the
  issue only calls out the test report as stale, not the verdict, and
  there's no review to re-run since a fresh review would need another test
  pass first (which is bounded by `max_fix_iterations`).
- No new dependencies, no changes outside `examples/software_factory/`.

### Full diff shape

- Add the `max_fix_iterations < 1` guard near the top of
  `software_factory`, right after the docstring, before `write_plan(...)`.
- Replace the existing `for attempt in range(max_fix_iterations): ... pr =
  fix(...)` block with the same loop plus an `else:` clause that performs
  the final `run_tests` call, as shown above.
- No other lines in `pipeline.py` change; `metadata` construction after the
  loop (`pipeline.py:435-438`) stays the same since `tests`/`verdict` are
  now always safely bound.

## Documentation updates

`examples/software_factory/README.md`, section "Bounded fix loop with
deterministic step ids" (`README.md:233-246`), shows the loop body as a code
snippet. Since the loop's shape changes (new `else` clause), update that
snippet to match the new code exactly, and add a short sentence noting that
`max_fix_iterations` must be at least 1 and that a final `run_tests_final`
run happens if the loop exhausts without an approved review, e.g.:

> Each invocation inside the loop carries an explicit `id=`, so a resumed
> run matches the same step runs. `max_fix_iterations` must be at least 1.
> If the loop exhausts its iterations without an approved review, the last
> action taken is always `fix`, so one more `run_tests` call (`id=
> "run_tests_final"`) runs after the loop to keep the deploy approval's test
> report in sync with the final state of the branch:

followed by the updated code snippet (including the `else:` block).

No other README sections reference `max_fix_iterations` or the loop
internals, so no further doc changes are needed (confirmed by grepping the
example folder).

## Tests to add

`examples/software_factory/` has no existing automated test suite, and the
pipeline's steps are thin wrappers around live sandbox sessions, the
`claude` CLI agent, and the GitHub API (`factory_utils.py`). This falls
under the CLAUDE.md testing exception for "code involves integrations with
external services" — full end-to-end automated coverage would require
mocking sandboxes, agent streaming output, and GitHub, which is
disproportionate to a minimal, localized loop-control-flow fix and is out
of scope per the issue's "keep the change minimal" instruction. Instead:

1. **Manual/local verification** (no new files):
   - Trace both edge cases by hand against the new code:
     - `max_fix_iterations=0` → `ValueError` raised immediately, before any
       step runs.
     - `max_fix_iterations=1` (or any N) with a scenario where tests keep
       failing (or reviews are never approved) through the last attempt →
       confirm the loop's `else` branch fires and a `run_tests_final` step
       is scheduled after `fix_{N-1}`.
     - `max_fix_iterations=N` with an approval on the final attempt →
       confirm the loop `break`s and the `else` branch does *not* run (no
       redundant `run_tests_final`).
   - If a sandbox stack, GitHub token, and Claude agent credentials are
     available locally, run `python examples/software_factory/run.py
     --max-fix-iterations 0 ...` against a scratch repo/issue and confirm
     the pipeline fails fast with the new `ValueError` message instead of a
     `NameError`. Then run with a small `max_fix_iterations` value and a
     `--test-command` that's guaranteed to fail (e.g. `false`) to confirm a
     `run_tests_final` step shows up in the run before the `deploy_approval`
     wait step, and that its `TestReport` (not an older one) is what's
     shown in the approval metadata.
2. **Lint check**: run `ruff check examples` and `ruff format examples
   --check` (as done by `scripts/lint.sh`) on the modified file, since
   `examples/` is linted (though not type-checked) in CI.

If reviewers want a lower-cost automated signal, a follow-up (out of scope
for this minimal fix) could add a `tests/unit/examples/software_factory/`
suite that monkeypatches the module-level step names (`write_plan`,
`open_workspace`, `implement`, `run_tests`, `review`, `fix`,
`close_workspace`, `deploy`) and `wait` in `pipeline.py` with lightweight
fake `@step`-decorated doubles, then exercises `software_factory(...)`
directly the same way `tests/unit/pipelines/dynamic/test_pipeline.py`
exercises other dynamic pipelines. That's a larger, separate change and not
part of this fix.

## Step-by-step implementation checklist

1. Open `examples/software_factory/pipeline.py`.
2. Add the `max_fix_iterations < 1` guard at the top of `software_factory`,
   right after the docstring.
3. Convert the `for attempt in range(max_fix_iterations): ...` loop to
   include an `else:` clause that calls `run_tests(..., id="run_tests_final")`.
4. Re-read the function to confirm `tests` and `verdict` are always bound
   before the `metadata` construction, and that no other code paths were
   changed.
5. Update `examples/software_factory/README.md`, "Bounded fix loop with
   deterministic step ids" section, to match the new loop shape and mention
   the `max_fix_iterations >= 1` requirement and the final test re-run.
6. Run `bash scripts/format.sh` and `ruff check examples` /
   `ruff format examples --check` on the touched files.
7. Manually trace/verify both edge cases as described above (and, if
   feasible locally, do a live run with `--max-fix-iterations 0` and a
   failing `--test-command`).
8. Run `/simplify` on the diff before opening the PR, per project
   guidelines.
