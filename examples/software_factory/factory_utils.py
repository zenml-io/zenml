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
"""Shared helpers for the software factory pipeline steps."""

import base64
import json
import os
import re
import tempfile
import threading
from typing import Any, Dict, List, Optional
from uuid import UUID

import markdown
from models import PRRef

from zenml import get_step_context, log_metadata
from zenml.client import Client
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.logger import get_logger
from zenml.sandboxes import BaseSandbox, SandboxOutput, SandboxSession
from zenml.types import HTMLString
from zenml.utils.dashboard_utils import get_run_url

logger = get_logger(__name__)

REPO_DIR = "repo"
RESULT_DIR = ".factory"
PLAN_DIR = "spec/plans"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
AGENT_AUTH_ENV_VARS = ["CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"]


def active_sandbox() -> BaseSandbox:
    """Return the active stack's sandbox component.

    Raises:
        RuntimeError: If the active stack has no sandbox component.

    Returns:
        The active stack's sandbox component.
    """
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError("No Sandbox component in the active stack.")
    return sandbox


def refresh_sandbox_client(sandbox: BaseSandbox) -> None:
    """Drop the cached Kubernetes API client of the sandbox component.

    Args:
        sandbox: The sandbox component.
    """
    # TODO: Move this into KubernetesSandbox.get_kube_client in the main
    # repo. The cached client carries a presigned EKS token that expires
    # after 15 minutes while connector_has_expired() tracks the longer STS
    # session, so the first attach after a long step fails with a 401.
    try:
        from zenml.integrations.kubernetes.sandboxes.kubernetes_sandbox import (
            KubernetesSandbox,
        )
    except ImportError:
        return

    if isinstance(sandbox, KubernetesSandbox):
        sandbox._k8s_client = None


def attach_sandbox(workspace: str) -> SandboxSession:
    """Attach to a sandbox session with a fresh API client.

    Args:
        workspace: The id of the sandbox session.

    Returns:
        The attached session.
    """
    sandbox = active_sandbox()
    refresh_sandbox_client(sandbox)
    return sandbox.attach(workspace)


def github_token() -> str:
    """Read the GitHub token from the step environment.

    Raises:
        RuntimeError: If the token environment variable is not set.

    Returns:
        The GitHub token.
    """
    try:
        return os.environ[GITHUB_TOKEN_ENV]
    except KeyError:
        raise RuntimeError(f"{GITHUB_TOKEN_ENV} is not set.") from None


def run_command(
    session: SandboxSession,
    command: List[str],
    cwd: Optional[str] = REPO_DIR,
    env: Optional[Dict[str, str]] = None,
    check: bool = True,
) -> SandboxOutput:
    """Run a command in the sandbox session and collect its output.

    Args:
        session: The sandbox session to run the command in.
        command: The command to run.
        cwd: Working directory for the command, relative to the session.
        env: Environment variables to set for the command.
        check: Whether to raise when the command exits with a non-zero code.

    Raises:
        RuntimeError: If `check` is set and the command exits with a
            non-zero code.

    Returns:
        The collected command output.
    """
    output = session.exec(command, cwd=cwd, env=env).collect()
    if check and output.exit_code != 0:
        raise RuntimeError(
            f"Command failed (exit {output.exit_code}): {output.stderr}"
        )
    return output


def git_auth_env() -> Dict[str, str]:
    """Environment that authenticates a single git command against GitHub.

    Returns:
        Git config environment variables carrying the token.
    """
    # The token is passed per command and never written to the checkout,
    # so the agent running in the same checkout cannot push or read it.
    credentials = base64.b64encode(
        f"x-access-token:{github_token()}".encode()
    ).decode()
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.extraheader",
        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credentials}",
    }


def clone_repo(
    session: SandboxSession, repo: str, ref: Optional[str] = None
) -> None:
    """Clone a GitHub repository into the session working directory.

    Args:
        session: The sandbox session to clone into.
        repo: The repository to clone, `owner/name`.
        ref: Branch to clone. Defaults to the repository's default branch.
    """
    command = ["git", "clone"]
    if ref:
        command += ["--branch", ref]
    command += [f"https://github.com/{repo}", REPO_DIR]
    run_command(session, command, cwd=None, env=git_auth_env())
    run_command(session, ["git", "config", "user.name", "software-factory"])
    run_command(
        session,
        [
            "git",
            "config",
            "user.email",
            "software-factory@users.noreply.github.com",
        ],
    )
    run_command(
        session, ["bash", "-c", f"echo {RESULT_DIR}/ >> .git/info/exclude"]
    )


def default_branch(session: SandboxSession, repo: str) -> str:
    """Look up a GitHub repository's default branch.

    Args:
        session: The sandbox session to run `gh` in.
        repo: The repository to query, `owner/name`.

    Returns:
        The name of the repository's default branch.
    """
    output = run_command(
        session,
        [
            "gh",
            "repo",
            "view",
            repo,
            "--json",
            "defaultBranchRef",
            "--jq",
            ".defaultBranchRef.name",
        ],
        cwd=None,
        env={"GH_TOKEN": github_token()},
    )
    return output.stdout.strip()


def resolve_base_branch(
    session: SandboxSession, repo: str, base_branch: Optional[str]
) -> str:
    """Resolve the branch that work branches are created from and merged into.

    Args:
        session: The sandbox session to run `gh` in.
        repo: The repository to query, `owner/name`.
        base_branch: The configured base branch, if any.

    Returns:
        The configured base branch, or the repository's default branch.
    """
    return base_branch or default_branch(session, repo)


def branch_exists(session: SandboxSession, branch: str) -> bool:
    """Check whether a branch exists on the origin remote.

    Args:
        session: The sandbox session to run `git` in.
        branch: The branch name to check.

    Returns:
        Whether the branch exists on origin.
    """
    output = run_command(
        session,
        ["git", "ls-remote", "--heads", "origin", branch],
        env=git_auth_env(),
    )
    return bool(output.stdout.strip())


def attach_or_recreate(
    workspace: str, repo: str, branch: str
) -> SandboxSession:
    """Reattach to the shared workspace session, or recreate it.

    Args:
        workspace: The session id of the shared workspace.
        repo: The repository the workspace tracks, `owner/name`.
        branch: The branch the workspace tracks.

    Returns:
        A sandbox session checked out to `branch`. A recreated session is
        destroyed when its context manager exits, an attached one is closed.
    """
    try:
        session = attach_sandbox(workspace)
    except (KeyError, RuntimeError) as e:
        logger.warning(
            "Could not attach to sandbox session `%s`: %s Recreating the "
            "workspace from a fresh clone.",
            workspace,
            e,
        )
        session = active_sandbox().create_session(destroy_on_exit=True)
        clone_repo(session, repo, ref=branch)

    run_command(session, ["git", "fetch", "origin"], env=git_auth_env())
    run_command(session, ["git", "checkout", branch])
    run_command(session, ["git", "reset", "--hard", f"origin/{branch}"])
    return session


def render_agent_event(event: Dict[str, Any]) -> List[str]:
    """Render one stream-json event of the agent CLI as log lines.

    Args:
        event: The decoded event.

    Returns:
        Log lines for the event.
    """
    event_type = event.get("type")
    if event_type == "assistant":
        rendered = []
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "text" and block.get("text", "").strip():
                rendered.append(f"[assistant] {block['text'].strip()}")
            elif block.get("type") == "tool_use":
                rendered.append(
                    f"[tool] {block.get('name')} "
                    f"{_summarize_tool_input(block.get('input', {}))}"
                )
        return rendered

    if event_type == "result":
        return [
            f"[result] {event.get('subtype')} after "
            f"{event.get('num_turns')} turns"
        ]

    return []


def _summarize_tool_input(tool_input: Dict[str, Any]) -> str:
    """Summarize a tool call input for the log.

    Args:
        tool_input: The tool input.

    Returns:
        A short description of the input.
    """
    for key in ("command", "file_path", "path", "pattern", "description"):
        if key in tool_input:
            return str(tool_input[key])[:200]

    return json.dumps(tool_input)[:200]


def agent_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract model, token and cost figures from the agent's result event.

    Args:
        result: The `result` event emitted by the agent CLI.

    Returns:
        Metadata describing the agent invocation.
    """
    usage = result.get("usage", {})
    # The CLI also bills small helper calls to a cheaper model. Report the
    # model that did the actual work.
    model_usage: Dict[str, Dict[str, Any]] = result.get("modelUsage", {})
    model = max(
        model_usage, key=lambda m: model_usage[m]["costUSD"], default="unknown"
    )
    return {
        "model": model,
        "turns": result.get("num_turns", 0),
        "duration_s": round(result.get("duration_ms", 0) / 1000, 1),
        "cost_usd": round(result.get("total_cost_usd", 0.0), 4),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
        "cache_write_tokens": usage.get("cache_creation_input_tokens", 0),
    }


def run_agent(
    session: SandboxSession, prompt: str, model: str, cwd: str = REPO_DIR
) -> None:
    """Run the agent CLI non-interactively, stream its output, log its usage.

    Model, turn count, token counts, cost and duration are attached to the
    calling step run as metadata under the `agent` key. Results are read
    from files the agent writes, see the prompts in `pipeline.py`.

    Args:
        session: The sandbox session to run the agent in.
        prompt: The prompt to pass to the agent.
        model: The model alias or id the agent should use.
        cwd: Working directory for the agent, relative to the session.

    Raises:
        RuntimeError: If the agent exits with a non-zero code.
    """
    command = [
        "claude",
        "-p",
        prompt,
        "--model",
        model,
        "--dangerously-skip-permissions",
        "--output-format",
        "stream-json",
        "--verbose",
    ]
    env = {
        name: os.environ[name]
        for name in AGENT_AUTH_ENV_VARS
        if name in os.environ
    }
    process = session.exec(command, cwd=cwd, env=env)
    # Drain stderr concurrently so a chatty CLI cannot fill the pipe and
    # block while stdout is being read.
    stderr_lines: List[str] = []
    stderr_thread = threading.Thread(
        target=lambda: stderr_lines.extend(process.stderr()), daemon=True
    )
    stderr_thread.start()
    result: Dict[str, Any] = {}
    for line in process.stdout():
        try:
            event = json.loads(line)
        except ValueError:
            logger.info(line.rstrip("\n"))
            continue
        for rendered in render_agent_event(event):
            logger.info(rendered)
        if event.get("type") == "result":
            result = event
    stderr_thread.join()
    exit_code = process.wait()
    if exit_code != 0:
        stderr = "".join(stderr_lines)
        raise RuntimeError(f"Agent failed (exit {exit_code}): {stderr}")

    if result:
        metadata = agent_metadata(result)
        logger.info(
            "Agent used %s for %s turns, %s input / %s output tokens, "
            "$%s, %ss.",
            metadata["model"],
            metadata["turns"],
            metadata["input_tokens"],
            metadata["output_tokens"],
            metadata["cost_usd"],
            metadata["duration_s"],
        )
        log_metadata(metadata={"agent": metadata})


def log_agent_totals(run_id: UUID) -> Dict[str, Any]:
    """Sum the agent usage of all steps of a run and log it on the run.

    Args:
        run_id: The pipeline run.

    Returns:
        The summed cost, tokens, turns and duration under the `agent_total`
        key, plus the number of agent invocations.
    """
    totals = {
        "cost_usd": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "turns": 0,
        "duration_s": 0.0,
        "invocations": 0,
    }
    for step in Client().get_pipeline_run(run_id).steps.values():
        usage = step.run_metadata.get("agent")
        if not isinstance(usage, dict):
            continue
        totals["invocations"] += 1
        for key in totals:
            if key in usage:
                totals[key] += usage[key]
    totals["cost_usd"] = round(totals["cost_usd"], 4)
    totals["duration_s"] = round(totals["duration_s"], 1)
    log_metadata(
        metadata={"agent_total": totals}, run_id_name_or_prefix=run_id
    )
    return totals


def markdown_to_html(text: str, title: str) -> HTMLString:
    """Render Markdown as a self-contained HTML page for the dashboard.

    The dashboard's own Markdown view styles fenced code blocks poorly, so
    plan-like artifacts are also stored as HTML with explicit code styling.

    Args:
        text: The Markdown source.
        title: The page title.

    Returns:
        The rendered page.
    """
    body = markdown.markdown(text, extensions=["fenced_code", "tables"])
    style = (
        "body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;"
        "max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.5;"
        "color:#1f2933}"
        "pre{background:#f4f6f8;border:1px solid #d9dee3;border-radius:6px;"
        "padding:12px;overflow-x:auto}"
        "code{font-family:SFMono-Regular,Consolas,Menlo,monospace;"
        "font-size:0.9em}"
        ":not(pre)>code{background:#f4f6f8;padding:1px 4px;border-radius:4px}"
        "table{border-collapse:collapse}td,th{border:1px solid #d9dee3;"
        "padding:4px 8px}"
    )
    return HTMLString(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>{style}</style></head>"
        f"<body>{body}</body></html>"
    )


def read_repo_file(session: SandboxSession, path: str) -> str:
    """Download a file from the checkout and return its text.

    Args:
        session: The sandbox session to download from.
        path: The file path, relative to the repository root.

    Raises:
        RuntimeError: If the file does not exist.

    Returns:
        The text content of the file.
    """
    remote_path = os.path.join(REPO_DIR, path)
    with tempfile.TemporaryDirectory() as tmp_dir:
        local_path = os.path.join(tmp_dir, os.path.basename(path))
        try:
            session.download_file(remote_path, local_path)
        except Exception as e:
            raise RuntimeError(
                f"File `{remote_path}` does not exist in the checkout."
            ) from e
        with open(local_path) as f:
            return f.read()


def write_repo_file(session: SandboxSession, path: str, content: str) -> None:
    """Write a text file into the checkout.

    Args:
        session: The sandbox session to upload to.
        path: The file path, relative to the repository root.
        content: The text content to write.
    """
    directory = os.path.dirname(path)
    if directory:
        run_command(session, ["mkdir", "-p", directory])
    with tempfile.TemporaryDirectory() as tmp_dir:
        local_path = os.path.join(tmp_dir, os.path.basename(path))
        with open(local_path, "w") as f:
            f.write(content)
        session.upload_file(local_path, os.path.join(REPO_DIR, path))


def commit_all(session: SandboxSession, message: str) -> bool:
    """Stage and commit all changes in the checkout.

    Args:
        session: The sandbox session to commit in.
        message: The commit message.

    Returns:
        Whether a commit was created. False when there was nothing to commit.
    """
    status = run_command(session, ["git", "status", "--porcelain"])
    if not status.stdout.strip():
        return False
    run_command(session, ["git", "add", "-A"])
    run_command(session, ["git", "commit", "-m", message])
    return True


def push_branch(session: SandboxSession, branch: str) -> None:
    """Push a branch to origin with a command-scoped token.

    Args:
        session: The sandbox session to push from.
        branch: The branch to push.
    """
    run_command(
        session, ["git", "push", "-u", "origin", branch], env=git_auth_env()
    )


def branch_for_issue(issue: str) -> str:
    """Derive a work branch name from the first line of an issue.

    Args:
        issue: The issue description.

    Returns:
        A branch name like `factory/add-health-check-endpoint`.
    """
    title = issue.strip().splitlines()[0].lower()
    slug = re.sub(r"[^a-z0-9]+", "-", title).strip("-")[:50].rstrip("-")
    return f"factory/{slug or 'issue'}"


def plan_path(branch: str) -> str:
    """Path of the committed plan file for a work branch.

    Args:
        branch: The work branch.

    Returns:
        The plan file path, relative to the repository root.
    """
    return f"{PLAN_DIR}/{branch.replace('/', '-')}.md"


def run_url() -> Optional[str]:
    """Dashboard URL of the current pipeline run.

    Returns:
        The run URL, or None if the server has no dashboard.
    """
    return get_run_url(get_step_context().pipeline_run)


def pr_body(summary: str, branch: str, run: Optional[str]) -> str:
    """Build the pull request body from the agent summary.

    Args:
        summary: The agent's summary of the changes on the branch.
        branch: The work branch.
        run: The dashboard URL of the pipeline run, if any.

    Returns:
        The pull request body.
    """
    body = f"## Summary\n\n{summary.strip()}\n\nPlan: `{plan_path(branch)}`\n"
    if run:
        body += f"\nRun: {run}\n"

    return body


def open_pr(
    session: SandboxSession,
    repo: str,
    branch: str,
    base: str,
    title: str,
    body: str,
) -> PRRef:
    """Open a draft pull request, or update the body of the existing one.

    Args:
        session: The sandbox session to run `gh` in.
        repo: The repository to open the pull request against, `owner/name`.
        branch: The head branch of the pull request.
        base: The base branch of the pull request.
        title: The pull request title.
        body: The pull request body.

    Returns:
        A reference to the open pull request.
    """
    env = {"GH_TOKEN": github_token()}
    existing = run_command(
        session,
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "url,number",
        ],
        env=env,
    )
    pull_requests = json.loads(existing.stdout)
    if not pull_requests:
        run_command(
            session,
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--draft",
                "--head",
                branch,
                "--base",
                base,
                "--title",
                title,
                "--body",
                body,
            ],
            env=env,
        )
    else:
        run_command(
            session,
            ["gh", "pr", "edit", branch, "--repo", repo, "--body", body],
            env=env,
        )

    view = run_command(
        session,
        ["gh", "pr", "view", branch, "--repo", repo, "--json", "url,number"],
        env=env,
    )
    return PRRef.model_validate_json(view.stdout)


def destroy_workspace_hook(exception: Optional[BaseException] = None) -> None:
    """Destroy the shared workspace session when the run ends.

    Args:
        exception: The exception that ended the run, if any.
    """
    try:
        context = DynamicPipelineRunContext.get()
        if context is None:
            return

        run = Client().get_pipeline_run(context.run.id)
        step_run = run.steps.get("open_workspace")
        if step_run is None:
            return

        output = step_run.regular_outputs.get("workspace")
        if output is None:
            return

        workspace = output.load()
        try:
            session = attach_sandbox(workspace)
        except (KeyError, RuntimeError):
            logger.info(
                "Shared workspace session `%s` is not running.", workspace
            )
            return

        session.destroy()
    except Exception as e:
        logger.warning("Failed to destroy the shared workspace session: %s", e)
