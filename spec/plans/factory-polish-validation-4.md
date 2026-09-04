# Plan: Fix edge cases in the software factory fix loop

## Root cause

`software_factory` (`examples/software_factory/pipeline.py:355-448`) drives a
test/review/fix loop:

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

Two bugs fall out of this shape:

1. **`max_fix_iterations=0` → `NameError`.** If the loop body never executes
   (`range(0)` is empty), `tests` is never bound, but it's referenced
   unconditionally afterwards in `tests.load().model_dump()`. This raises
   `NameError: name 'tests' is not defined` when building the
   `deploy_approval` metadata.

2. **Stale test report after the last fix.** If the loop runs out of
   iterations while the last action taken was `fix` (i.e. it never hit the
   `break`), no `run_tests` call happens after that final `fix`. The `tests`
   variable used in the `deploy_approval` metadata still reflects the state
   of the branch *before* the last fix was applied, which misrepresents the
   branch that's actually being proposed for deploy.

Note that a `for...else` block in Python runs the `else` clause exactly when
the loop completes without hitting `break` — which is precisely the "last
action was a fix" condition. That's the natural, minimal way to express fix
#2 without extra flags.

## Code changes (all within `examples/software_factory/pipeline.py`)

1. **Validate `max_fix_iterations` up front.** At the very start of
   `software_factory`, before any step is invoked, add:

   ```python
   if max_fix_iterations < 1:
       raise ValueError("max_fix_iterations must be at least 1.")
   ```

   This fails fast with a clear error instead of letting the pipeline run
   partway and then hit a `NameError` deep in metadata construction. Update
   the `max_fix_iterations` docstring entry to note the `>= 1` constraint,
   e.g. "The maximum number of test and review fix iterations. Must be at
   least 1."

2. **Run tests once more if the loop ended on a `fix`.** Convert the `for`
   loop to use a `for...else`, and in the `else` branch call `run_tests`
   again with a distinct step id, reassigning `tests`:

   ```python
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

   Since `max_fix_iterations >= 1` is now guaranteed, `tests` is always bound
   by the time the loop finishes (either from the last loop iteration or from
   the `else` branch), so the `NameError` from bug #1 can't occur even as a
   secondary effect of this change.

   Scope note: only `tests` is refreshed here, matching what the issue asks
   for. `verdict` is intentionally left as whatever it was set to inside the
   loop (i.e. `None`, or the last rejected review) — that's pre-existing
   behavior for the "ran out of iterations" case and isn't part of what's
   reported as misleading; re-reviewing after the final fix is out of scope
   for a minimal change.

3. No changes needed to `deploy_approval` metadata construction itself —
   once `tests` is always bound, `tests.load().model_dump()` is safe.

## README update

`examples/software_factory/README.md`, section "Bounded fix loop with
deterministic step ids" (around line 233), shows the loop as sample code.
Since the loop shape changes (added `else` clause), update the snippet to
match:

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
    tests = run_tests(..., id="run_tests_final")
```

Add a short sentence noting that `max_fix_iterations` must be at least 1, and
that the `else` branch re-runs tests once more with a distinct id when the
loop's last action was a fix, so `deploy_approval` always reflects the final
state of the branch.

## Tests to add

Look for existing tests for this example (check
`tests/` for `software_factory` or example-level pipeline tests; if none
exist yet, add a new test module, e.g.
`tests/unit/examples/software_factory/test_pipeline.py`, mirroring how other
dynamic-pipeline examples are tested — likely by invoking `software_factory`
against a fake/mocked step layer, since the real steps hit sandboxes,
GitHub, and Claude). Concretely add tests that:

1. **`max_fix_iterations=0` raises a clear error.** Call `software_factory`
   (or invoke the pipeline function directly if it can be unit-tested
   without a full run) with `max_fix_iterations=0` and assert a `ValueError`
   is raised with a message mentioning `max_fix_iterations`, and that no
   steps are executed beforehand (or at least that no `NameError` occurs).

2. **Negative `max_fix_iterations` also raises.** Same as above with `-1`,
   to confirm the `< 1` check (not just `== 0`).

3. **Final test re-run happens when the loop exhausts on a `fix`.** Mock/fake
   `run_tests`, `review`, and `fix` such that every review is rejected (or
   every test run fails) across all `max_fix_iterations` attempts, run the
   pipeline with e.g. `max_fix_iterations=2`, and assert:
   - `run_tests` is called `max_fix_iterations + 1` times total.
   - The last `run_tests` call uses `id="run_tests_final"`.
   - The `deploy_approval` wait step's metadata `tests` reflects the result
     of that final call (not the one from the last loop iteration).

4. **No extra test run when the loop breaks early.** Mock the loop so that
   the review is approved on, say, the first attempt (`break` hits), run the
   pipeline with `max_fix_iterations > 1`, and assert `run_tests` is called
   exactly once (i.e. the `else` branch of the `for` loop does *not* run),
   confirming the `for...else` behaves as expected and doesn't add a
   redundant test run on the success path.

5. **Regression check for `max_fix_iterations=1` exhausting via fix.** A
   dedicated minimal case: one iteration, tests fail (or review rejects),
   `fix` runs, loop exhausts without `break`, and the final `run_tests_final`
   call still occurs and its result is what's used downstream — this is the
   simplest reproduction of the original bug report's second issue.

If the test harness for this example only supports invoking the annotated
pipeline through ZenML's dynamic-pipeline test utilities (rather than calling
the plain function), structure the fakes/mocks around whatever pattern
existing example pipeline tests already use in this repo — check
`tests/unit/` for other `examples/*/pipeline.py` coverage before deciding
between "call the undecorated function directly" vs. "run the pipeline
end-to-end with stubbed steps."
