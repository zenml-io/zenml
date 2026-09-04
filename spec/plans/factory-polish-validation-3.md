# Plan: Fix edge cases in the software factory fix loop

## Root cause

In `examples/software_factory/pipeline.py`, the `software_factory` dynamic
pipeline function (lines ~400-433) has a `for attempt in
range(max_fix_iterations):` loop that assigns the local variables `tests` and
`verdict`, both of which are read after the loop when building the
`deploy_approval` metadata (line 436-438: `tests.load()...`,
`verdict.load()...`).

1. **`max_fix_iterations == 0`**: `range(0)` never executes the loop body, so
   `tests` is never bound. `tests.load()` at line 436 then raises
   `NameError: name 'tests' is not defined`. `verdict` is pre-initialized to
   `None` (line 400) so it doesn't have the same problem, but `tests` does
   not have a fallback.

2. **Loop exhausted, last action was a fix**: When the loop runs out of
   attempts (`attempt == max_fix_iterations - 1`) and that final iteration
   ends by calling `fix(...)` (i.e., tests failed, or tests passed but the
   review was not approved), the branch now has uncommitted-to-history state
   from that fix that has never been tested. The `tests` variable used in the
   `deploy_approval` metadata still holds the *pre-fix* test report from
   `run_tests_{attempt}`, which is stale/misleading — a human approving the
   deploy sees a test report that doesn't reflect the code they're about to
   ship.

## Fix approach

Keep the change minimal and contained to
`examples/software_factory/pipeline.py`.

### 1. Guard `max_fix_iterations`

Validate that `max_fix_iterations >= 1` at the top of `software_factory`
(after the docstring, before any steps run) and raise a clear `ValueError` if
not. This is preferable to making the metadata construction tolerate a
missing `tests`/`verdict` because:
- A `TestReport`-less deploy approval would be a materially different
  (weaker) contract for anyone reviewing/approving the wait step.
- Zero fix iterations means "never test or review the implementation before
  asking to deploy," which is very likely a misconfiguration worth failing
  fast on, rather than silently proceeding with no test data.

```python
if max_fix_iterations < 1:
    raise ValueError(
        "max_fix_iterations must be at least 1, got "
        f"{max_fix_iterations}."
    )
```

Place this check near the top of the function body, before `write_plan(...)`
is invoked, so it fails immediately without wasting a sandbox session or
agent call.

### 2. Re-run tests after a trailing fix

Track whether the *last action taken inside the loop* was a `fix(...)` call.
Reset the flag at the top of each iteration and set it right after the `fix`
call, so it reflects only the final iteration's outcome (it must not leak
`True` from an earlier iteration into a later one that ends via `break`):

```python
verdict = None
fixed_last = False
for attempt in range(max_fix_iterations):
    fixed_last = False
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
    fixed_last = True

if fixed_last:
    tests = run_tests(
        workspace=workspace,
        repo=repo,
        branch=target_branch,
        test_command=test_command,
        id="run_tests_final",
    )

close_workspace(workspace=workspace)
```

Notes:
- `run_tests_final` is a distinct, deterministic step id as required, so
  resumed runs still match the same step runs (consistent with the "Bounded
  fix loop with deterministic step ids" convention already documented in the
  README).
- `verdict` is intentionally left as whatever it was when the loop exited
  (`None` if the trailing fix followed a test failure, or the unapproved
  `ReviewVerdict` if it followed a rejected review) — the fix step already
  received it as input, and the deploy-approval metadata block below still
  only includes `verdict` when it is not `None`, so no change needed there.
- This extra `run_tests` call only happens when the loop actually ends on a
  fix; the normal case (breaking out after an approved review) is unaffected
  and does not gain an extra test run.

### 3. No changes needed to the `deploy_approval` metadata block

Once `max_fix_iterations >= 1` is enforced and the trailing re-test is added,
`tests` is always bound by the time the metadata dict is built, and it always
reflects the latest state of the branch. The existing code:

```python
pr_result = pr.load()
metadata = {"pr_url": pr_result.url, "tests": tests.load().model_dump()}
if verdict is not None:
    metadata["verdict"] = verdict.load().model_dump()
```

remains correct as-is.

## Tests to add

There isn't an existing unit test file for this example pipeline (it's an
`examples/` sandbox-driven pipeline, not covered by `/tests/unit`), so add
lightweight tests that exercise the pipeline's loop *logic* in isolation
without needing a real sandbox — following the "generally test integrations
extensively locally" guidance, but since this is plain Python control flow
(not an external-service integration), it should get direct coverage:

1. Check whether `examples/software_factory/` already has any test files
   (`tests/` folder in the example dir) before deciding where new tests go.
   If none exist, create `examples/software_factory/tests/test_pipeline.py`
   (or similar) that:
   - Imports `software_factory` and calls it (or refactors the validation
     into a small importable helper if the pipeline function itself is hard
     to invoke without ZenML runtime) to assert `ValueError` is raised when
     `max_fix_iterations=0`.
   - If the pipeline body can't be unit-tested directly without a ZenML run
     (likely, since steps are decorated with `@step`/`@pipeline`), consider
     extracting the `max_fix_iterations` validation into a small pure
     function (e.g. `_validate_max_fix_iterations(max_fix_iterations: int) ->
     None`) that can be unit-tested directly, and call it from
     `software_factory`. This keeps the change minimal while still giving
     the guard clause direct test coverage.
2. For the "final re-test after trailing fix" behavior, since it depends on
   ZenML's dynamic-pipeline step execution, prefer a targeted manual/local
   verification (e.g., running the example pipeline against a local sandbox
   with `max_fix_iterations=1` and a failing `test_command` that always
   fails, then confirming two `run_tests_*` step runs appear:
   `run_tests_0` and `run_tests_final`) over trying to unit test dynamic
   pipeline orchestration. Document this manual check in the PR description
   if no automated test is feasible for the orchestration path itself.

## Documentation update

Update `examples/software_factory/README.md`, section "Bounded fix loop with
deterministic step ids" (around line 233), to reflect the new loop shape:
add the `max_fix_iterations >= 1` validation and the trailing
`run_tests_final` call to the code sample, e.g.:

```python
if max_fix_iterations < 1:
    raise ValueError("max_fix_iterations must be at least 1")

verdict = None
fixed_last = False
for attempt in range(max_fix_iterations):
    fixed_last = False
    tests = run_tests(..., id=f"run_tests_{attempt}")
    verdict = None
    if tests.load().passed:
        verdict = review(..., tests=tests, id=f"review_{attempt}")
        if verdict.load().approved:
            break
    pr = fix(..., tests=tests, verdict=verdict, id=f"fix_{attempt}")
    fixed_last = True

if fixed_last:
    tests = run_tests(..., id="run_tests_final")
```

and add a sentence explaining why the extra re-test exists (so the
`deploy_approval` wait always reflects the latest test run, not a stale one
from before the last fix).

## Summary of concrete steps

1. In `examples/software_factory/pipeline.py`, add a `max_fix_iterations < 1`
   validation with a clear `ValueError` near the top of `software_factory`.
2. Add a `fixed_last` boolean flag inside the fix loop: reset to `False` at
   the top of each iteration, set to `True` immediately after the `fix(...)`
   call.
3. After the loop and before `close_workspace(...)`, if `fixed_last` is
   `True`, call `run_tests(..., id="run_tests_final")` again and reassign
   `tests` to its result.
4. Leave the `deploy_approval` metadata construction unchanged — it already
   handles `verdict is None` and will now always have a valid `tests` value.
5. Update `examples/software_factory/README.md`'s "Bounded fix loop with
   deterministic step ids" section to show the updated loop shape and to
   note the new `run_tests_final` step id.
6. Add/extend tests: unit-test the `max_fix_iterations` validation (extracting
   it to a small pure helper if needed for testability); manually verify the
   `run_tests_final` behavior against a local sandbox run since it depends on
   dynamic pipeline orchestration.
7. Run `bash scripts/format.sh` and targeted tests before committing.
