#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Dynamic pipeline that drives a GitHub issue through an agent workflow."""

from typing import Annotated, Optional, Tuple

from factory_utils import (
    active_sandbox,
    attach_or_recreate,
    attach_sandbox,
    branch_exists,
    branch_for_issue,
    clone_repo,
    commit_all,
    destroy_workspace_hook,
    github_token,
    issue_from_webhook_body,
    log_agent_totals,
    markdown_to_html,
    open_pr,
    plan_path,
    pr_body,
    push_branch,
    read_repo_file,
    resolve_base_branch,
    run_agent,
    run_command,
    run_url,
    write_repo_file,
)
from models import PRRef, Review, ReviewVerdict, TestReport

from zenml import add_tags, pipeline, step, wait
from zenml.config import DockerSettings
from zenml.config.retry_config import StepRetryConfig
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.logger import get_logger
from zenml.types import HTMLString, MarkdownString

logger = get_logger(__name__)


@step
def issue_from_event(
    repo: str,
) -> Tuple[Annotated[str, "repo"], Annotated[str, "issue"]]:
    """Read the issue from the webhook delivery that started this run.

    Used when the run was started by a webhook trigger instead of with an
    explicit `issue` parameter, for example from a GitHub issue, a Slack
    message or an emoji reaction on one. Needs a ZenML Pro server with
    webhooks.

    Args:
        repo: The repository configured on the snapshot, used when the
            delivery names none.

    Raises:
        RuntimeError: If the run was not started by a webhook trigger.

    Returns:
        The repository and the issue text.
    """
    # Imported here so the example also imports on servers without webhooks.
    from zenml.utils.trigger_utils import get_raw_webhook_event

    delivery = get_raw_webhook_event()
    if delivery is None:
        raise RuntimeError(
            "No issue was given and this run was not started by a webhook "
            "trigger. Pass the `issue` parameter."
        )
    repo, issue = issue_from_webhook_body(delivery["body"], default_repo=repo)
    return repo, issue


@step(
    secrets=["github", "claude"],
    retry=StepRetryConfig(max_retries=2, delay=5),
)
def write_plan(
    repo: str,
    issue: str,
    agent_model: str,
    base_branch: Optional[str] = None,
) -> Tuple[
    Annotated[MarkdownString, "plan"],
    Annotated[HTMLString, "plan_preview"],
]:
    """Draft a fix plan for a GitHub issue in a fresh sandbox session.

    Args:
        repo: The repository to work in, `owner/name`.
        issue: The issue description.
        agent_model: The model the agent uses.
        base_branch: The branch to plan against, the default branch if unset.

    Returns:
        The plan written by the agent and an HTML rendering of it.
    """
    session = active_sandbox().create_session()
    try:
        clone_repo(session, repo, ref=base_branch)
        prompt = (
            "You are working on the GitHub issue below. Investigate the "
            "repository and write a plan that describes the root cause, the "
            "code changes to make and the tests to add, broken into "
            "concrete steps.\n\n"
            f"Issue:\n{issue}\n\n"
            "Write your result to the file .factory/plan.md relative to the "
            "repository root."
        )
        run_agent(session, prompt, model=agent_model)
        plan = read_repo_file(session, ".factory/plan.md")
        return MarkdownString(plan), markdown_to_html(plan, title="Plan")
    finally:
        session.destroy()


@step(secrets=["github"])
def open_workspace(
    repo: str,
    branch: str,
    plan: MarkdownString,
    base_branch: Optional[str] = None,
) -> Tuple[Annotated[str, "workspace"], Annotated[str, "base_branch"]]:
    """Create the shared workspace session, check out the branch, commit the plan.

    Args:
        repo: The repository to work in, `owner/name`.
        branch: The branch to check out or create.
        plan: The plan for the issue.
        base_branch: The branch to create `branch` from, the default branch
            if unset.

    Returns:
        The id of the shared workspace session and the resolved base branch.
    """
    session = active_sandbox().create_session()
    base = resolve_base_branch(session, repo, base_branch)
    clone_repo(session, repo, ref=base)
    if branch_exists(session, branch):
        run_command(session, ["git", "checkout", branch])
    else:
        run_command(session, ["git", "checkout", "-b", branch])
    write_repo_file(session, plan_path(branch), plan)
    commit_all(session, "Add plan")
    push_branch(session, branch)
    workspace = session.id
    session.close()
    return workspace, base


@step(
    secrets=["github", "claude"],
    retry=StepRetryConfig(max_retries=2, delay=5),
)
def implement(
    workspace: str,
    repo: str,
    branch: str,
    issue: str,
    plan: MarkdownString,
    base_branch: str,
    agent_model: str,
) -> Annotated[PRRef, "pr"]:
    """Implement the plan and open a draft pull request.

    Args:
        workspace: The id of the shared workspace session.
        repo: The repository to work in, `owner/name`.
        branch: The branch to work on.
        issue: The issue description.
        plan: The plan for the issue.
        base_branch: The pull request base.
        agent_model: The model the agent uses.

    Returns:
        A reference to the opened pull request.
    """
    with attach_or_recreate(workspace, repo, branch) as session:
        prompt = (
            "You are working on the GitHub issue below, given the plan. "
            "Make the code changes described in the plan in the current "
            "checkout. Add or update tests for the changes. Do not commit. "
            "Do not push.\n\n"
            f"Issue:\n{issue}\n\n"
            f"Plan:\n{plan}\n\n"
            "When you are done, write a short summary of the changes you "
            "made, as bullet points without headings, to the file "
            ".factory/summary.md relative to the repository root."
        )
        run_agent(session, prompt, model=agent_model)
        summary = read_repo_file(session, ".factory/summary.md")
        commit_all(session, f"Implement: {issue.splitlines()[0]}")
        push_branch(session, branch)
        return open_pr(
            session,
            repo,
            branch,
            base_branch,
            title=issue.splitlines()[0],
            body=pr_body(summary, branch, run_url()),
        )


@step(secrets=["github"])
def run_tests(
    workspace: str,
    repo: str,
    branch: str,
    test_command: Optional[str] = None,
) -> Annotated[TestReport, "tests"]:
    """Run the test command in the checkout.

    Args:
        workspace: The id of the shared workspace session.
        repo: The repository to work in, `owner/name`.
        branch: The branch to work on.
        test_command: Shell command that runs the tests. Tests are skipped
            if unset.

    Returns:
        The result of the test run.
    """
    if not test_command:
        return TestReport(passed=True, summary="No test command set.")

    with attach_or_recreate(workspace, repo, branch) as session:
        output = run_command(
            session, ["bash", "-lc", test_command], check=False
        )
        combined = (output.stdout + output.stderr)[-4000:]
        return TestReport(passed=output.exit_code == 0, summary=combined)


@step(
    secrets=["github", "claude"],
    retry=StepRetryConfig(max_retries=2, delay=5),
)
def review(
    workspace: str,
    repo: str,
    branch: str,
    issue: str,
    plan: MarkdownString,
    tests: TestReport,
    base_branch: str,
    agent_model: str,
) -> Annotated[ReviewVerdict, "verdict"]:
    """Review the diff on the branch against the issue, plan and test report.

    Args:
        workspace: The id of the shared workspace session.
        repo: The repository to work in, `owner/name`.
        branch: The branch to work on.
        issue: The issue description.
        plan: The plan for the issue.
        tests: The result of the latest test run.
        base_branch: The branch to diff against.
        agent_model: The model the agent uses.

    Returns:
        The verdict of the review.
    """
    with attach_or_recreate(workspace, repo, branch) as session:
        diff = run_command(
            session, ["git", "diff", f"origin/{base_branch}...HEAD"]
        ).stdout[:20000]
        prompt = (
            "You are reviewing the code changes for the GitHub issue "
            "below, given the plan and test report. Inspect the diff and "
            "decide whether the changes are ready to merge.\n\n"
            f"Issue:\n{issue}\n\n"
            f"Plan:\n{plan}\n\n"
            f"Test report:\n{tests.summary}\n\n"
            f"Diff:\n{diff}\n\n"
            'Your result must be a JSON object with the keys "approved" '
            '(boolean) and "comments" (a list of strings).\n'
            "Write your result to the file .factory/review.json relative "
            "to the repository root."
        )
        run_agent(session, prompt, model=agent_model)
        result = read_repo_file(session, ".factory/review.json")
        return ReviewVerdict.model_validate_json(result)


@step(
    secrets=["github", "claude"],
    retry=StepRetryConfig(max_retries=2, delay=5),
)
def fix(
    workspace: str,
    repo: str,
    branch: str,
    issue: str,
    tests: TestReport,
    base_branch: str,
    agent_model: str,
    verdict: Optional[ReviewVerdict] = None,
) -> Annotated[PRRef, "pr"]:
    """Address review and test feedback and update the pull request.

    Args:
        workspace: The id of the shared workspace session.
        repo: The repository to work in, `owner/name`.
        branch: The branch to work on.
        issue: The issue description.
        tests: The result of the latest test run.
        base_branch: The pull request base.
        agent_model: The model the agent uses.
        verdict: The verdict of the latest review, unset if the tests failed.

    Returns:
        A reference to the updated pull request.
    """
    with attach_or_recreate(workspace, repo, branch) as session:
        comments = "none"
        if verdict is not None:
            comments = "\n".join(
                f"- {comment}" for comment in verdict.comments
            )
        prompt = (
            "You are addressing test failures and review feedback for the "
            "GitHub issue below. Make the necessary code changes in the "
            "current checkout. Add or update tests for the changes. Do not "
            "commit. Do not push.\n\n"
            f"Issue:\n{issue}\n\n"
            f"Test report:\n{tests.summary}\n\n"
            f"Review comments:\n{comments}\n\n"
            "When you are done, write a short summary of all changes on "
            "this branch, as bullet points without headings, to the file "
            ".factory/summary.md relative to the repository root."
        )
        run_agent(session, prompt, model=agent_model)
        summary = read_repo_file(session, ".factory/summary.md")
        commit_all(session, "Fix: address review and test feedback")
        push_branch(session, branch)
        return open_pr(
            session,
            repo,
            branch,
            base_branch,
            title=issue.splitlines()[0],
            body=pr_body(summary, branch, run_url()),
        )


@step
def close_workspace(workspace: str) -> None:
    """Destroy the shared workspace session.

    Args:
        workspace: The id of the shared workspace session.
    """
    try:
        session = attach_sandbox(workspace)
    except (KeyError, RuntimeError) as e:
        logger.warning(
            "Could not attach to sandbox session `%s`: %s", workspace, e
        )
        return
    session.destroy()


@step(secrets=["github"])
def deploy(pr: PRRef, repo: str) -> None:
    """Mark the pull request ready for review.

    Args:
        pr: The pull request to deploy.
        repo: The repository of the pull request, `owner/name`.
    """
    # TODO: Replace with the actual deployment. Marking the pull request
    # ready for review stands in for it.
    logger.info("Deploying %s (#%s)", pr.url, pr.number)
    with active_sandbox().create_session(destroy_on_exit=True) as session:
        run_command(
            session,
            ["gh", "pr", "ready", str(pr.number), "--repo", repo],
            cwd=None,
            env={"GH_TOKEN": github_token()},
        )


@pipeline(
    dynamic=True,
    enable_cache=False,
    on_end=destroy_workspace_hook,
    settings={
        "docker": DockerSettings(
            python_package_installer="uv",
            requirements="requirements.txt",
        ),
    },
)
def software_factory(
    repo: str,
    issue: Optional[str] = None,
    target_branch: Optional[str] = None,
    base_branch: Optional[str] = None,
    test_command: Optional[str] = None,
    max_fix_iterations: int = 2,
    agent_model: str = "sonnet",
    gate_timeout: int = 600,
) -> None:
    """Drive a GitHub issue through plan, implement, test and review.

    Args:
        repo: The repository to work in, `owner/name`. A GitHub issue
            delivery overrides it with the issue's repository.
        issue: The issue description. The first line is the title. Read
            from the webhook delivery that started the run if unset.
        target_branch: The branch to work on. Created from the base branch
            if it does not exist, checked out if it does. Derived from the
            issue title if unset, for example
            `factory/add-health-check-endpoint`.
        base_branch: The branch to create `target_branch` from and to open
            the pull request against. The repository's default branch if
            unset.
        test_command: Shell command that runs the tests in the checkout.
            Tests are skipped if unset.
        max_fix_iterations: The maximum number of fix rounds. Tests and
            review run once more than this, so the last fix is always
            tested. Zero means test and review only.
        agent_model: The model alias or id the agent uses, for example
            `sonnet`, `opus` or a full model id.
        gate_timeout: Seconds each approval gate polls for an answer before
            the run is paused.
    """
    context = DynamicPipelineRunContext.get()
    assert context is not None
    if not issue:
        repo_output, issue_output = issue_from_event(repo=repo)
        repo, issue = repo_output.load(), issue_output.load()
    target_branch = target_branch or branch_for_issue(issue)
    add_tags(tags=[repo, target_branch], run=context.run.id)

    plan, _ = write_plan(
        repo=repo,
        issue=issue,
        agent_model=agent_model,
        base_branch=base_branch,
    )
    plan_review = wait(
        schema=Review,
        question="Approve plan?",
        metadata={"plan": plan.load()},
        name="plan_review",
        timeout=gate_timeout,
    )
    if not plan_review.approved:
        return

    workspace, base_branch = open_workspace(
        repo=repo, branch=target_branch, plan=plan, base_branch=base_branch
    )
    pr = implement(
        workspace=workspace,
        repo=repo,
        branch=target_branch,
        issue=issue,
        plan=plan,
        base_branch=base_branch,
        agent_model=agent_model,
    )
    # One more test and review round than fixes, so the loop never ends
    # on an untested fix.
    for attempt in range(max_fix_iterations + 1):
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
                agent_model=agent_model,
                id=f"review_{attempt}",
            )
            if verdict.load().approved:
                break
        if attempt == max_fix_iterations:
            break
        pr = fix(
            workspace=workspace,
            repo=repo,
            branch=target_branch,
            issue=issue,
            tests=tests,
            base_branch=base_branch,
            agent_model=agent_model,
            verdict=verdict,
            id=f"fix_{attempt}",
        )
    close_workspace(workspace=workspace)

    pr_result = pr.load()
    totals = log_agent_totals(context.run.id)
    metadata = {
        "pr_url": pr_result.url,
        "tests": tests.load().model_dump(),
        "agent_total": totals,
    }
    if verdict is not None:
        metadata["verdict"] = verdict.load().model_dump()
    deploy_approval = wait(
        schema=bool,
        question=(
            f"Deploy {pr_result.url}? The agent used {totals['turns']} turns "
            f"and ${totals['cost_usd']} across {totals['invocations']} calls."
        ),
        metadata=metadata,
        name="deploy_approval",
        timeout=gate_timeout,
    )
    if deploy_approval:
        deploy(pr=pr, repo=repo)
