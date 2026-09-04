# Plan: Fix edge cases in the software factory fix loop

## Root cause

`examples/software_factory/pipeline.py:355-448` defines the `software_factory`
dynamic pipeline. The test/review/fix loop is:

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
if verdict is not None:
    metadata["verdict"] = verdict.load().model_dump()
deploy_approval = wait(..., metadata=metadata, ...)
```

Two bugs fall out of this shape:

1. **`max_fix_iterations == 0` → `NameError`.** `tests` is a loop-local
   variable, first bound inside the `for` body. If the range is empty (i.e.
   `max_fix_iterations <= 0`), the loop body never executes, so `tests` is
   never assigned. `tests.load().model_dump()` at line 436 then raises
   `NameError: name 'tests' is not defined`. `max_fix_iterations` has no
   validation and a caller passing `0` (or a negative number) hits this
   directly.

2. **Stale test report after the final fix.** The loop always exits either by
   `break` (an approved review — `tests` reflects the code that was
   reviewed and approved, which is correct) or by falling off the end after
   the last `attempt` calls `fix(...)`. In the fall-off-the-end case, `fix`
   pushes a new commit that has never been tested — the last `tests` value in
   scope is the *pre-fix* report from `run_tests_{attempt}` earlier in that
   same iteration. The `deploy_approval` wait step then shows a test report
   that doesn't correspond to the branch's current HEAD, which is misleading
   for whoever approves the deploy.

Both bugs are about the loop's exit state not being tracked/handled
explicitly. The fix needs to (a) make `max_fix_iterations == 0` well-defined
without crashing, and (b) make sure that whenever the loop's last action was
a `fix`, tests are re-run once more before building `deploy_approval`
metadata.

## Design decision

- For (1): validate `max_fix_iterations >= 1` and raise a clear
  `ValueError` early, before entering the loop. This is simpler and more
  minimal than making the metadata construction tolerate a missing `tests`
  variable (which would require sentinel values and conditionals sprinkled
  through metadata construction, and would let the pipeline proceed to
  "deploy" a PR that was never tested — worse behavior than failing fast).
  The docstring for `max_fix_iterations` should note the minimum.
- For (2): track whether the loop's last action was a `fix` (i.e., it did not
  `break` out on an approved review). If so, after the loop and before
  building `deploy_approval` metadata, call `run_tests` one more time with a
  distinct step id (`run_tests_final`) and use that report in the metadata
  instead of the stale one from inside the loop.

## Code changes (`examples/software_factory/pipeline.py`)

1. Add validation immediately after the docstring, before `plan = write_plan(...)`
   or right after entering the pipeline body (before the loop is reached is
   sufficient; do it early, near the top of the function body):

   ```python
   if max_fix_iterations < 1:
       raise ValueError(
           "`max_fix_iterations` must be at least 1, got "
           f"{max_fix_iterations}."
       )
   ```

   Update the parameter docstring to mention the constraint:
   `max_fix_iterations: The maximum number of test and review fix
   iterations. Must be at least 1.`

2. Track loop exit state so we know if the last action was `fix`. Introduce a
   boolean, e.g. `needs_final_tests`, set it `True` right before/after each
   `fix(...)` call and `False` right before `break`:

   ```python
   verdict = None
   needs_final_tests = False
   for attempt in range(max_fix_iterations):
       tests = run_tests(
           workspace=workspace,
           repo=repo,
           branch=target_branch,
           test_command=test_command,
           id=f"run_tests_{attempt}",
       )
       verdict = None
       needs_final_tests = False
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
       needs_final_tests = True

   if needs_final_tests:
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
   - `needs_final_tests` is reset to `False` at the top of every iteration
     (alongside `verdict = None`) and only set `True` right after `fix` runs,
     so it always reflects whether the *very last* action in the loop was a
     `fix` call, regardless of which attempt it happened on or whether the
     loop exited via `break` or by exhausting the range.
   - When the loop exits via `break` (approved review), `needs_final_tests`
     is `False`, so no extra `run_tests` call happens — behavior for the
     already-working "approved" path is unchanged.
   - When `max_fix_iterations` iterations all end in `fix` without approval,
     `needs_final_tests` is `True` after the loop, so `run_tests_final` runs
     once, using the same `tests` variable name so the rest of the function
     (the `metadata` construction) needs no further changes.
   - `verdict` still correctly stays `None` in this case (it's reset to
     `None` at the top of the last iteration and never reassigned before
     falling out of the loop), so the existing `if verdict is not None:`
     branch in the metadata construction is unaffected.
   - Since `max_fix_iterations >= 1` is now enforced, `tests` is always bound
     by the time metadata is built — no `NameError` possible.
   - Keep the extra `run_tests` call outside/after the loop but before
     `close_workspace`, since `run_tests` needs the still-open `workspace`
     session.

3. No changes needed to `metadata` construction itself
   (`examples/software_factory/pipeline.py:436-438`) — it already does
   `tests.load().model_dump()`, and `tests` now always reflects the final
   state of the branch.

## Documentation changes (`examples/software_factory/README.md`)

The loop shape changes (an extra conditional `run_tests_final` call after the
loop), so update the "Bounded fix loop with deterministic step ids" section
(`examples/software_factory/README.md:233-246`) to show the corrected shape,
e.g.:

```python
verdict = None
needs_final_tests = False
for attempt in range(max_fix_iterations):
    tests = run_tests(..., id=f"run_tests_{attempt}")
    verdict = None
    needs_final_tests = False
    if tests.load().passed:
        verdict = review(..., tests=tests, id=f"review_{attempt}")
        if verdict.load().approved:
            break
    pr = fix(..., tests=tests, verdict=verdict, id=f"fix_{attempt}")
    needs_final_tests = True

if needs_final_tests:
    tests = run_tests(..., id="run_tests_final")
```

Add a short sentence noting that `max_fix_iterations` must be at least 1, and
that a final `run_tests_final` run happens when the loop's last action was a
`fix`, so the `deploy_approval` metadata always reflects the tested state of
the branch's current HEAD.

## Tests to add

There's no existing unit test module for this example
(`tests/` has no `software_factory` coverage), and the pipeline function
directly calls sandbox-backed steps (`write_plan`, `implement`, `run_tests`,
etc.), which are integration-style and require a live sandbox/agent per the
project convention ("code involves integrations with external services" —
tested locally/in CI by the developer, not via unit tests).

Given that, the pragmatic, minimal test surface is a fast, isolated unit test
of the *validation* behavior only, since that's plain Python logic with no
external dependencies:

1. Add `tests/unit/examples/test_software_factory_pipeline.py` (new file,
   mirroring the `tests/unit/...` convention) with:
   - A test that calls `software_factory.entrypoint` (or invokes the
     pipeline's underlying function directly, without triggering a real run)
     with `max_fix_iterations=0` and asserts it raises `ValueError` with a
     message mentioning `max_fix_iterations`.
   - A test with `max_fix_iterations=-1` asserting the same.
   - If invoking the pipeline entrypoint directly is impractical because of
     `@pipeline`/dynamic-pipeline decoration side effects (e.g. requiring an
     active ZenML client/run context), factor the validation into a small
     top-level helper (e.g. `_validate_max_fix_iterations(max_fix_iterations:
     int) -> None`) defined next to `software_factory` in
     `pipeline.py`, call it from the pipeline body, and unit test the helper
     directly. This keeps the test fast and independent of sandbox/agent
     infrastructure while still exercising the exact logic used in
     production.

2. Manual/CI verification (documented in the PR description rather than an
   automated test, consistent with the project's guidance for
   integration-heavy code): run the example end-to-end once with
   `max_fix_iterations=1` where the first `fix` is expected to exhaust the
   budget (e.g. by pointing `test_command` at a check that keeps failing),
   and confirm in the run logs that a `run_tests_final` step executes after
   the last `fix_0` step, and that the `deploy_approval` wait step's
   `tests` metadata matches the output of `run_tests_final`, not
   `run_tests_0`.

## Summary of files touched

- `examples/software_factory/pipeline.py`: add `max_fix_iterations`
  validation, track loop exit state, run `run_tests_final` when needed.
- `examples/software_factory/README.md`: update the "Bounded fix loop with
  deterministic step ids" section to reflect the new loop shape and document
  the `max_fix_iterations >= 1` constraint.
- `tests/unit/examples/test_software_factory_pipeline.py` (new): unit tests
  for the `max_fix_iterations` validation.
