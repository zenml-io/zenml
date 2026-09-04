# Fix edge cases in the software factory fix loop

## Root cause

In `examples/software_factory/pipeline.py`, the `software_factory` pipeline
runs a `for attempt in range(max_fix_iterations):` loop that assigns the
local variable `tests` on every iteration and conditionally calls `fix`.
After the loop, the pipeline unconditionally does `tests.load()` to build
the `deploy_approval` metadata. Two edge cases break this:

1. **`max_fix_iterations == 0`** — `range(0)` never executes the loop body,
   so `tests` is never bound. `tests.load()` below the loop then raises
   `NameError: name 'tests' is not defined`.

2. **Loop exhausted on a `fix` iteration** — every non-`break` path through
   the loop body ends with a call to `fix(...)`. `fix` does not re-run
   tests, it just pushes a new commit. So when the loop runs out of
   `max_fix_iterations` without an approved review, the `tests` object used
   in the `deploy_approval` metadata is a stale report from *before* the
   final `fix`, not a report of the state actually being proposed for
   deployment. This is misleading for whoever approves the deploy.

Both edge cases stem from the same structural issue: the loop is the only
place that produces a `TestReport`, but the loop can end (or never start)
without the current branch state having been tested.

## Fix

Both edge cases can be handled with one structural change: use the `for
...  else:` construct. The `else` clause of a `for` loop runs whenever the
loop finishes **without** hitting `break` — which is exactly "loop
exhausted" (edge case 2) and also covers "loop never ran because
`max_fix_iterations == 0`" (edge case 1), since a zero-iteration loop also
never breaks.

Combine this with an explicit minimum check on `max_fix_iterations`, since
a fix loop that cannot run at all (0 iterations) is nonsensical for this
pipeline (there would never be an implement→test→review cycle) and silently
"handling" it by only running the final tests would hide a likely
misconfiguration. Fail fast, before any sandbox/agent work happens.

### Concrete steps

1. **Validate `max_fix_iterations` early.**
   At the very top of `software_factory`, before `write_plan` is called,
   add:

   ```python
   if max_fix_iterations < 1:
       raise ValueError(
           "max_fix_iterations must be at least 1, got "
           f"{max_fix_iterations}."
       )
   ```

   This gives a clear, immediate error instead of a `NameError` deep in
   the pipeline, and avoids wasting a `write_plan` sandbox run on a
   misconfigured pipeline.

2. **Add a final test run via `for...else` after the fix loop.**
   Change:

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
       # Every non-`break` path above ends with `fix`, which does not
       # re-run tests. Re-run tests here so `deploy_approval` reflects
       # the branch's actual final state rather than a stale report from
       # before the last fix (or, if max_fix_iterations was exhausted
       # with zero iterations, the only test run at all).
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
   - `tests` is now guaranteed to be assigned by the time
     `close_workspace`/`deploy_approval` metadata construction run, for
     every value of `max_fix_iterations >= 1` (guaranteed by step 1).
   - No other control flow changes: `break` still only happens on an
     approved review, so the `else` only fires when the loop is exhausted
     or never entered — precisely the cases described in the issue.
   - `verdict` semantics are unchanged: it stays `None` unless the last
     *loop* iteration produced a review; the final `else`-branch test run
     does not set `verdict`, so `deploy_approval` metadata correctly omits
     `verdict` when the branch was never approved.

3. **No other files need to change.** The fix is entirely within
   `examples/software_factory/pipeline.py`; `models.py`, `factory_utils.py`,
   and the `deploy_approval`/`metadata` construction below the loop need no
   changes since `tests` is now always defined.

## README update

Update `examples/software_factory/README.md`, section
"### Bounded fix loop with deterministic step ids" (around line 233-246), to
show the new loop shape (the `else` clause and `run_tests_final` id) and to
mention the `max_fix_iterations >= 1` requirement. Replace the existing code
block:

```python
for attempt in range(max_fix_iterations):
    tests = run_tests(..., id=f"run_tests_{attempt}")
    verdict = None
    if tests.load().passed:
        verdict = review(..., tests=tests, id=f"review_{attempt}")
        if verdict.load().approved:
            break
    pr = fix(..., tests=tests, verdict=verdict, id=f"fix_{attempt}")
```

with:

```python
for attempt in range(max_fix_iterations):
    tests = run_tests(..., id=f"run_tests_{attempt}")
    verdict = None
    if tests.load().passed:
        verdict = review(..., tests=tests, id=f"review_{attempt}")
        if verdict.load().approved:
            break
    pr = fix(..., tests=tests, verdict=verdict, id=f"fix_{attempt}")
else:
    # Loop exhausted without an approved review: the last action was
    # always `fix`, so re-run tests to reflect the branch's final state.
    tests = run_tests(..., id="run_tests_final")
```

and add a sentence noting that `max_fix_iterations` must be at least 1
(the pipeline raises `ValueError` otherwise), and that the `else` branch
re-tests the branch after the loop's last `fix` so `deploy_approval`'s
metadata is never stale.

## Tests to add

Add tests near wherever existing `software_factory` pipeline-level tests
live (check `tests/unit/` — if a pipeline construction/dry-run smoke test
exists for `examples/software_factory`, extend it; otherwise these can be
plain unit tests that import the module and exercise the pipeline function
in dynamic/compile mode, mocking the underlying steps).

1. **`max_fix_iterations == 0` raises `ValueError`.**
   Call `software_factory(..., max_fix_iterations=0)` (or however the
   dynamic pipeline is invoked/compiled in the existing test harness for
   this example) and assert a `ValueError` is raised with a message
   mentioning `max_fix_iterations`, before any step (e.g. `write_plan`) is
   invoked — assert the mocked `write_plan`/steps were never called.

2. **Negative `max_fix_iterations` also raises `ValueError`.**
   Same as above with e.g. `max_fix_iterations=-1`, to confirm the check is
   `< 1` and not just `== 0`.

3. **Loop exhausted on a `fix` iteration triggers `run_tests_final`.**
   Mock `run_tests`, `review`, and `fix` so that every `review` call
   returns `approved=False` (or every `run_tests` call returns
   `passed=False`) for `max_fix_iterations=2`. Assert:
   - `run_tests` is called 3 times total: `run_tests_0`, `run_tests_1`,
     and `run_tests_final` (by inspecting the `id=` kwarg each call was
     made with).
   - The metadata passed to the `deploy_approval` `wait(...)` call reflects
     the `TestReport` returned by the `run_tests_final` invocation, not the
     one from `run_tests_1`.

4. **Loop exits via `break` does not trigger a final test run.**
   Mock `run_tests` (passed=True) and `review` (approved=True) on the
   first iteration with `max_fix_iterations=3`. Assert `run_tests` is
   called exactly once (`run_tests_0`) and no `run_tests_final` /
   `fix` call happens, i.e. behavior for the already-working happy path is
   unchanged.

If no existing test infrastructure invokes this dynamic pipeline function
directly (dynamic pipelines commonly need a `SANDBOX`/mocked orchestration
context), scope the new tests to whatever mocking pattern
`tests/unit/examples/` (or similar) already uses for this example; if none
exists yet, a minimal test can monkeypatch `factory_utils`/step functions
referenced via `zenml.step`-decorated functions' `.entrypoint` or invoke the
pipeline in a `with pipeline.testing_context(...)`-style harness consistent
with how other dynamic ZenML pipelines in this repo are unit-tested — grep
`tests/unit` for other `dynamic=True` pipeline tests before inventing a new
pattern.
