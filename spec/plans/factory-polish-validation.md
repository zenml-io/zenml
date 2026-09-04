# Fix edge cases in the software factory fix loop

## Root cause

`software_factory` (`examples/software_factory/pipeline.py:355-448`) drives the
test/review/fix loop with:

```python
verdict = None
for attempt in range(max_fix_iterations):
    tests = run_tests(..., id=f"run_tests_{attempt}")
    verdict = None
    if tests.load().passed:
        verdict = review(..., tests=tests, id=f"review_{attempt}")
        if verdict.load().approved:
            break
    pr = fix(..., tests=tests, verdict=verdict, id=f"fix_{attempt}")
close_workspace(workspace=workspace)

pr_result = pr.load()
metadata = {"pr_url": pr_result.url, "tests": tests.load().model_dump()}
```

Two bugs fall out of this:

1. **`max_fix_iterations=0` → `NameError`.** `tests` is only ever bound
   inside the loop body. If the loop runs zero times, `tests` is never
   assigned, and `tests.load()` when building `metadata` raises
   `NameError: name 'tests' is not defined`. `verdict` doesn't have this
   problem because it's pre-initialized to `None` before the loop, but
   `tests` is not.

2. **Stale test report when the loop is exhausted on a `fix`.** The loop's
   only exit conditions are (a) `break` right after an *approved* review, or
   (b) the `for` running out of iterations. Every iteration that doesn't
   `break` ends by calling `fix(...)`. So whenever the loop is exhausted
   without a `break`, the last thing that happened on the branch was a
   `fix` call whose output was never re-tested. The `tests` variable used in
   `deploy_approval`'s metadata still holds the *pre-fix* report, which
   misrepresents the state of the branch being proposed for deploy.

## Fix

Both issues share one root cause: the loop has no step for "the loop ended
right after a fix, with no subsequent test run." Python's `for...else`
clause is a natural fit — `else` runs exactly when the loop finishes
*without* hitting `break`, which is precisely the set of cases where the
last action taken was a `fix` (including the zero-iteration case, where "the
last action" is vacuously true and no fix even ran).

Change the loop in `software_factory` (`examples/software_factory/pipeline.py`)
from:

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
    close_workspace(workspace=workspace)
```

to:

```python
    if max_fix_iterations < 1:
        raise ValueError(
            "`max_fix_iterations` must be at least 1, got "
            f"{max_fix_iterations}."
        )

    verdict = None
    tests = None
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
        # Reached only when the loop exhausted `max_fix_iterations` without
        # an approved review, i.e. the branch's last change was an
        # untested `fix`. Re-run tests so `deploy_approval` reflects the
        # branch's actual final state instead of a pre-fix report.
        tests = run_tests(
            workspace=workspace,
            repo=repo,
            branch=target_branch,
            test_command=test_command,
            id="run_tests_final",
        )
    close_workspace(workspace=workspace)
```

Notes on why this is minimal and correct:

- The explicit `max_fix_iterations < 1` guard gives a clear error message
  (per the issue's first acceptable option) instead of silently relying on
  the `for...else` fallback to paper over a nonsensical configuration where
  no fix loop can ever run at all. It also keeps `implement()`'s PR from
  being deployed without ever having been tested once.
- With the guard in place, `range(max_fix_iterations)` always has at least
  one iteration, so the `else` clause only fires in the "exhausted after a
  fix" case described in bug 2 — not in the zero-iteration case, which is
  now rejected earlier with a clear error.
- `tests = None` before the loop is defensive/documents intent; it is
  always overwritten before use once the `ValueError` guard is in place,
  but keeps the variable's existence obvious to a reader and avoids relying
  on the loop running at all.
- No new dependencies; the change is confined to `software_factory` in
  `examples/software_factory/pipeline.py`.

## Tests to add

`examples/software_factory` pipelines aren't unit-tested directly today (no
existing `tests/` coverage for this example — it's an integration-style
example driven by sandboxes/agents per the project's testing guidelines for
integration-heavy code). Given that, validate the two edge cases with a
small, focused unit test around the pure control-flow logic rather than
running the full pipeline:

1. Add `tests/unit/examples/test_software_factory_pipeline.py` (or the
   nearest existing convention for example pipelines, if one exists —
   check `tests/unit/` for a precedent first) that:
   - Calls `software_factory.entrypoint` (the undecorated function) — or
     extracts the loop into a tiny helper if the pipeline function can't be
     called directly outside a pipeline context — with
     `max_fix_iterations=0` and asserts it raises `ValueError` with a
     message mentioning `max_fix_iterations`, instead of `NameError`.
   - Simulates the "exhausted on a fix" path (`max_fix_iterations=1`,
     tests fail or review isn't approved) with mocked `run_tests`/`review`/
     `fix` steps and asserts `run_tests` is invoked a second time with
     `id="run_tests_final"` after the loop, so `deploy_approval`'s metadata
     is built from the post-fix report.
   - Simulates the "approved on first try" path and asserts the `else`
     branch's extra `run_tests_final` call does **not** happen (no
     redundant test run when the loop broke out normally).
2. If direct unit testing of the `dynamic=True` pipeline entrypoint proves
   impractical (e.g. it requires a live orchestration context), fall back
   to documenting manual verification steps in the PR description instead
   of forcing artificial coverage, consistent with the codebase guidance
   that integration-heavy code may rely on local/CI runs rather than unit
   tests. In that case, at minimum manually exercise:
   - `max_fix_iterations=0` → pipeline raises `ValueError` before creating
     any workspace/sandbox resources.
   - A run where the last loop iteration ends in `fix` (e.g.
     `max_fix_iterations=1` with a failing test command) → confirm a
     `run_tests_final` step appears in the run and `deploy_approval`'s
     metadata contains the post-fix test report.

## Documentation

Update the "Bounded fix loop with deterministic step ids" section in
`examples/software_factory/README.md` (around line 233) since the loop
shape changes:

- Extend the code snippet to include the `else` clause and the
  `run_tests_final` re-test call.
- Add a sentence noting that `max_fix_iterations` must be `>= 1` (invalid
  values raise `ValueError`), and that if the loop exhausts its iterations
  on a `fix`, tests are re-run once more (`id="run_tests_final"`) so the
  `deploy_approval` metadata reflects the branch's final state rather than
  a pre-fix report.
