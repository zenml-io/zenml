# Fix edge cases in the software factory fix loop

## Root cause

Both bugs live in the `software_factory` dynamic pipeline function in
`examples/software_factory/pipeline.py` (lines ~400-445), specifically in the
`for attempt in range(max_fix_iterations): ...` loop and the metadata built
for the `deploy_approval` wait condition right after it.

1. **`NameError` when `max_fix_iterations=0`.** `tests` is only ever assigned
   inside the loop body (`tests = run_tests(...)`, line 402). `verdict` is
   pre-initialized to `None` before the loop (line 400), but `tests` is not.
   When `max_fix_iterations` is `0`, `range(0)` is empty, the loop body never
   runs, and `tests` stays unbound. Execution reaches
   `metadata = {"pr_url": pr_result.url, "tests": tests.load().model_dump()}`
   (line 436) and raises `NameError: name 'tests' is not defined`.

2. **Stale test report when the loop exhausts on a `fix`.** Inside each
   iteration, `fix(...)` runs whenever the iteration does *not* `break` (i.e.
   whenever tests failed, or tests passed but the review wasn't approved).
   `break` is the only way to skip `fix` in a given iteration. So if the loop
   runs out of attempts without ever hitting `break`, the very last thing
   that happened on the branch is a `fix()` call — but the `tests` variable
   still holds the report from *before* that fix (either a failing run, or a
   passing run whose review was rejected). The `deploy_approval` wait
   condition (line 439) then shows a test report that doesn't reflect what's
   actually on the branch, which is misleading for whoever has to decide
   whether to deploy.

The issue text allows either fixing the metadata construction to tolerate a
missing `tests`/`verdict`, or requiring `max_fix_iterations >= 1`. This plan
picks explicit validation: `max_fix_iterations=0` disables the entire
test/review/fix loop, which silently changes the meaning of the pipeline
(nothing gets tested or reviewed before the deploy prompt) rather than being
a meaningful "run with zero iterations" configuration. A clear, fail-fast
error is more honest than quietly tolerating `None` tests/verdict in the
metadata. This also composes cleanly with the fix for bug 2 below (see the
`for...else` construct), which relies on the loop having run at least once.

## Code changes (`examples/software_factory/pipeline.py`)

### 1. Validate `max_fix_iterations` up front

Add a guard as the first statement in `software_factory`, before
`write_plan` is called, so a misconfigured run fails immediately instead of
after burning a plan-writing agent call and a human plan approval:

```python
def software_factory(
    repo: str,
    issue: str,
    target_branch: str,
    base_branch: Optional[str] = None,
    test_command: Optional[str] = None,
    max_fix_iterations: int = 3,
) -> None:
    """Drive a GitHub issue through plan, implement, test and review.

    Args:
        repo: The repository to work in, `owner/name`.
        issue: The issue description.
        target_branch: The branch to work on. Created from the base branch
            if it does not exist, checked out if it does.
        base_branch: The branch to create `target_branch` from and to open
            the pull request against. The repository's default branch if
            unset.
        test_command: Shell command that runs the tests in the checkout.
            Tests are skipped if unset.
        max_fix_iterations: The maximum number of test and review fix
            iterations.

    Raises:
        ValueError: If `max_fix_iterations` is less than 1.
    """
    if max_fix_iterations < 1:
        raise ValueError(
            "`max_fix_iterations` must be at least 1; the test, review and "
            "fix loop needs to run at least once to produce a test report "
            "for the deploy approval."
        )

    plan = write_plan(repo=repo, issue=issue, base_branch=base_branch)
    ...
```

(Only the `Raises` section is added to the docstring; `Args` is unchanged.)

### 2. Refresh the test report when the loop exhausts on a `fix`

Replace the `for` loop with a `for...else` (Python runs the `else` block only
when the loop completes without `break` — which, now that
`max_fix_iterations >= 1` is guaranteed, means the last thing that happened
was an unconditional `fix()` call):

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
        # Every attempt was used up and the last one ended with `fix`
        # (the only way to leave the loop without hitting `break` above).
        # Re-run the tests so the deploy_approval metadata reflects the
        # branch as it stands after that last fix, not the report from
        # before it.
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
- `verdict` is intentionally left as-is in the `else` branch (whatever the
  last iteration set it to, possibly `None`). The issue only asks to refresh
  the test report, not to force another review — re-reviewing would add a
  new agent call and iteration semantics that aren't part of this fix.
- The rest of the function (`close_workspace` onward, metadata construction,
  `deploy_approval` wait) needs no changes: `tests` is now always bound by
  the time it's read.
- No new imports or dependencies are needed.

## README changes (`examples/software_factory/README.md`)

1. In the "🔁 The Flow" intro paragraph (around line 38: *"The loop over
   `run_tests`, `review` and `fix` runs at most `max_fix_iterations` times
   and stops early on an approved review."*), add a sentence noting that
   `max_fix_iterations` must be at least 1, and that if the loop runs out of
   attempts on a `fix`, the tests are re-run once more (`run_tests_final`)
   before the deploy approval.
2. Update the "Bounded fix loop with deterministic step ids" section
   (currently lines 233-246) to show the `for...else` shape with
   `run_tests_final`, matching the new code in `pipeline.py`.
3. In the `deploy_approval` bullet under "🏃 Run It" (line 130: *"The wait
   condition carries the pull request URL, the last test report and the last
   review verdict."*), clarify that "last test report" means the report from
   `run_tests_final` when the loop was exhausted on a fix.

## Tests to add

`examples/software_factory/pipeline.py` has no existing automated test
coverage — end-to-end execution needs a live sandbox, the `claude` CLI and a
real GitHub repo/token, which is why the codebase's testing guidance
(exception for code integrating with external services) applies here. But
both bugs are pure Python control flow in the pipeline body, independent of
what the individual steps do internally, so they can be covered with a
hermetic unit test that swaps in fake step implementations:

1. Add `tests/unit/examples/software_factory/test_pipeline.py` (with the
   necessary `__init__.py` files, or a local `conftest.py`, mirroring the
   structure ZenML already uses for dynamic-pipeline tests in
   `tests/unit/execution/pipeline/dynamic/`).
2. Because `pipeline.py` uses bare imports (`from factory_utils import ...`,
   `from models import ...`) that only resolve when
   `examples/software_factory` is on `sys.path`, load it in the test via
   `importlib.util.spec_from_file_location` under a private module name
   (e.g. `_software_factory_pipeline_under_test`) with
   `monkeypatch.syspath_prepend("examples/software_factory")` scoped to the
   import, and restore `sys.path`/`sys.modules` afterwards. This avoids
   polluting the shared pytest process with generically-named modules like
   `models` or `factory_utils` that could collide with other examples.
3. After loading the module, monkeypatch every sandbox/GitHub/agent helper
   it imported (`active_sandbox`, `attach_sandbox`, `attach_or_recreate`,
   `branch_exists`, `clone_repo`, `commit_all`, `destroy_workspace_hook`,
   `github_token`, `open_pr`, `plan_path`, `pr_body`, `push_branch`,
   `read_repo_file`, `resolve_base_branch`, `run_agent`, `run_command`,
   `run_url`, `write_repo_file`) plus `wait` (from `zenml`) with lightweight
   fakes: `write_plan`/`open_workspace`/`implement` just need to return
   trivial values so the pipeline reaches the loop, and `wait` should
   auto-approve the `plan_review` schema so the run doesn't block.
4. Test cases:
   - `test_zero_max_fix_iterations_raises`: call the loaded
     `software_factory(..., max_fix_iterations=0)` and assert it raises
     `ValueError` before any step runs (no sandbox/agent fakes are even
     invoked — this is a good smoke test that the guard fires first).
   - `test_loop_exhausted_on_fix_reruns_tests`: monkeypatch the module's
     `run_tests`/`fix`/`review` step-equivalents (or drive `test_command`
     handling through a fake `run_command` that always returns a failing
     exit code) so every iteration fails tests and never gets an approved
     review; run with e.g. `max_fix_iterations=2`; assert the resulting
     `PipelineRunResponse.steps` contains a `run_tests_final` step whose
     recorded output matches the fake "final" test result, and that its
     upstream is `fix_1` (the last iteration's fix).
   - `test_loop_breaks_early_on_approval`: make the first iteration's tests
     pass and review get approved; assert the loop exits via `break`, that
     `run_tests_final` is *not* present in `run.steps`, and that the
     `deploy_approval` wait's metadata carries the `tests`/`verdict` from
     `attempt=0`.
5. Follow the existing pattern in
   `tests/unit/execution/pipeline/dynamic/test_sync_step_chaining.py` for
   asserting on `run.steps[...].spec.upstream_steps` and step presence.

## Manual verification (since full end-to-end coverage needs live infra)

Per the project's testing guidance for code that integrates with external
services, verify locally against a scratch repo before merging:

1. `python run.py --max-fix-iterations 0 ...` — should fail immediately with
   the new `ValueError` message, before any sandbox session is created (the
   guard runs before `write_plan`).
2. `python run.py --max-fix-iterations 1 --test-command "exit 1" ...` (a
   test command that always fails) — the loop should exhaust after one
   attempt ending in `fix`, and the run should show a `run_tests_final` step
   after the last `fix_0` step; the `deploy_approval` wait's metadata `tests`
   field should match that final run's report, not the pre-fix one.
3. `python run.py --max-fix-iterations 2 --test-command "true" ...` with a
   review that approves on the first attempt — confirm the loop still stops
   early via `break` and no `run_tests_final` step is created (unchanged
   behavior).
