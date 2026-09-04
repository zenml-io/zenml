# Plan: Fix edge cases in the software factory fix loop

## Root cause

`software_factory` (`examples/software_factory/pipeline.py:355-447`) builds a
`deploy_approval` metadata dict after a `for attempt in range(max_fix_iterations)`
loop that assigns `tests` (and conditionally `verdict`) only *inside* the loop
body:

```python
verdict = None
for attempt in range(max_fix_iterations):
    tests = run_tests(..., id=f"run_tests_{attempt}")
    verdict = None
    if tests.load().passed:
        verdict = review(..., id=f"review_{attempt}")
        if verdict.load().approved:
            break
    pr = fix(..., tests=tests, verdict=verdict, id=f"fix_{attempt}")
...
metadata = {"pr_url": pr_result.url, "tests": tests.load().model_dump()}
```

Two edge cases follow directly from this shape:

1. **`max_fix_iterations == 0`** — `range(0)` never executes, so `tests` is
   never bound. `tests.load()` at the metadata-construction line then raises
   `NameError: name 'tests' is not defined`, crashing the pipeline before it
   can even reach `deploy_approval`.

2. **Loop exhausted, last action was `fix`** — if every iteration fails to
   get an approved review (tests keep failing, or the reviewer keeps
   rejecting), the loop runs to completion without hitting `break`. The last
   statement executed is always `pr = fix(...)`, which mutates the branch.
   But `tests` still holds the *pre-fix* `TestReport` from the top of that
   same iteration — the fix step's changes were never re-tested. The
   `deploy_approval` wait step then shows a stale/misleading test report to
   the human approver, from before the branch's final state.

Both cases stem from the same structural gap: the loop has no "did we exit
via `break`, or did we run off the end" distinction, and no lower bound on
`max_fix_iterations`.

## Fix

Both edge cases can be closed with one minimal, structural change to the
loop in `software_factory`, using Python's `for...else` (the `else` clause
runs only when the loop completes *without* hitting `break` — i.e. exactly
the "last action was `fix`" case):

1. **Validate `max_fix_iterations` up front.** Raise a clear `ValueError` if
   `max_fix_iterations < 1`, right after entering `software_factory`, before
   `write_plan` is even called. This is preferable to the
   "tolerate missing `tests`/`verdict`" alternative because a 0-iteration
   fix loop is a meaningless configuration for this pipeline (there is
   nothing to show in `deploy_approval` if implementation was never tested
   or reviewed) — failing fast with a clear message is more honest than
   inventing placeholder metadata. This also makes edge case 1 impossible in
   the loop itself, since `range(max_fix_iterations)` is now guaranteed
   non-empty.

2. **Add a `for...else` clause after the loop** that re-runs `run_tests`
   with a distinct step id (`run_tests_final`) and reassigns `tests`,
   exactly when the loop ran to completion without a `break` (i.e. the last
   action was `fix`). When the loop exits via `break` (an approved review),
   the `else` clause is skipped and `tests` already reflects the
   post-fix/pre-approval state, so no extra work is needed there.

### Code changes — `examples/software_factory/pipeline.py`

In `software_factory`, right after the docstring (before `plan = write_plan(...)`):

```python
    if max_fix_iterations < 1:
        raise ValueError(
            "max_fix_iterations must be at least 1, got "
            f"{max_fix_iterations}."
        )
```

Replace the existing loop:

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
```

with:

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
        # The loop ran out of attempts without an approved review, so the
        # last action taken was `fix`. Re-run tests so `deploy_approval`
        # reflects the branch's actual final state instead of the report
        # from before that last fix.
        tests = run_tests(
            workspace=workspace,
            repo=repo,
            branch=target_branch,
            test_command=test_command,
            id="run_tests_final",
        )
```

No other lines need to change: `close_workspace`, the `pr_result`/`metadata`
construction, and `deploy_approval` all stay as-is — `tests` and `verdict`
are now guaranteed to be bound by the time they're read.

### README update — `examples/software_factory/README.md`

The "Bounded fix loop with deterministic step ids" section (around line 233)
currently shows the loop without the trailing re-test. Update the code
sample to match the new shape, e.g.:

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

Add a short sentence noting that `max_fix_iterations` must be `>= 1`, and
that the `else` branch (using the deterministic `run_tests_final` id) covers
the case where the loop exhausts its attempts on a `fix`, keeping the test
report shown at `deploy_approval` in sync with the branch's final state.

## Tests

This example has no existing automated test suite (`examples/software_factory/`
has no `tests/` directory, and there is no matching entry under
`/tests/unit` or `/tests/integration`). The pipeline's steps drive a live
sandbox and a Claude agent, which is exactly the kind of external-service
integration this repo's guidelines say to test locally/in CI rather than
via unit tests. Given that, keep verification proportional and minimal:

1. **Static/logic check (no sandbox needed):** since `max_fix_iterations`
   validation and the `for...else` control flow are pure Python, sanity
   check them directly by extracting the same loop shape into a throwaway
   script/REPL snippet substituting dummy `run_tests`/`review`/`fix`
   callables that just record calls, and asserting:
   - `max_fix_iterations=0` raises `ValueError` before any step call.
   - `max_fix_iterations=2` with tests always failing results in calls
     `run_tests_0, fix_0, run_tests_1, fix_1, run_tests_final` (else branch
     hit, final `tests` reflects the post-`fix_1` run).
   - `max_fix_iterations=2` with an approved review on the first attempt
     results in calls `run_tests_0, review_0` only (loop breaks, `else`
     skipped, no `run_tests_final`).
   This is a design-time sanity check, not a checked-in test, since the
   real function is a `@pipeline(dynamic=True)`-decorated function whose
   steps require a live stack/sandbox to execute meaningfully.
2. **Manual/local run:** run the example against a real or throwaway repo
   with `max_fix_iterations=0` and confirm it fails fast with the new
   `ValueError` message instead of a `NameError`. Then run with a low
   `test_command` that's guaranteed to fail (e.g. `exit 1`) and
   `max_fix_iterations=1`, and confirm in the run logs that a
   `run_tests_final` step executes after `fix_0`, and that the
   `deploy_approval` metadata's `tests` field matches that final run's
   summary rather than the pre-fix one.
3. **`bash scripts/format.sh` and `bash scripts/lint.sh`** (or targeted
   `ruff`/`mypy` on `examples/software_factory/pipeline.py`) to catch style
   or typing regressions from the edit, per project convention.
