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
"""PydanticAI agent with ZenML Sandbox-backed code-execution tools.

The agent has four tools backed by the active stack's Sandbox:

* ``run_python`` -- execute Python source, return stdout/stderr/exit code
* ``run_shell`` -- run a shell command, return stdout/stderr/exit code
* ``list_files`` -- list a directory inside the sandbox
* ``read_file`` -- read a file from the sandbox

All tools share a single live ``SandboxSession`` so files written in one
tool call persist for the next. That naturally drives multi-step
agent flows: generate data, inspect, filter, re-compute, etc.
"""

import shlex
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from zenml.client import Client
from zenml.sandboxes import SandboxSession

# Cap the stdout/stderr surface the agent sees per tool call. Passed to
# ``SandboxProcess.collect`` as ``max_chars`` -- the base helper drains
# both streams fully (so the provider's wait() doesn't block on a
# buffered reader) and flags per-stream truncation via ``SandboxOutput``.
_MAX_STREAM_CHARS = 32_000


class CodeResult(BaseModel):
    """Structured result returned by the ``run_python``/``run_shell`` tools."""

    stdout: str
    stderr: str
    exit_code: int


@dataclass
class AgentDeps:
    """Runtime handle passed to every tool call.

    Carries the live ``SandboxSession`` so all tool invocations share one
    container. A plain dataclass (not a Pydantic model) -- there's nothing
    to validate, and the live session isn't serializable anyway.
    """

    session: SandboxSession


def _exec_collect(session: SandboxSession, argv: list[str]) -> CodeResult:
    """Runs a command in the sandbox and folds the result into ``CodeResult``.

    Args:
        session: The live Sandbox session.
        argv: Command arguments to exec.

    Returns:
        Captured stdout/stderr/exit code, with truncation markers
        appended when the per-stream cap was hit.
    """
    process = session.exec(argv)
    out = process.collect(max_chars=_MAX_STREAM_CHARS)
    stdout = out.stdout
    if out.stdout_truncated:
        stdout += f"\n... [stdout truncated at {_MAX_STREAM_CHARS} chars]\n"
    stderr = out.stderr
    if out.stderr_truncated:
        stderr += f"\n... [stderr truncated at {_MAX_STREAM_CHARS} chars]\n"
    return CodeResult(stdout=stdout, stderr=stderr, exit_code=out.exit_code)


def build_agent() -> Agent[AgentDeps, str]:
    """Constructs the PydanticAI agent with the sandbox tools registered.

    Returns:
        A PydanticAI ``Agent`` wired up to drive a ZenML Sandbox session
        via four tools: run_python, run_shell, list_files, read_file.
    """
    agent: Agent[AgentDeps, str] = Agent(
        "openai:gpt-4o-mini",
        deps_type=AgentDeps,
        system_prompt=(
            "You are a data-analysis assistant operating inside a Linux "
            "sandbox running python:3.11-slim. The sandbox starts bare: "
            "only the Python standard library is available. If you need "
            "scientific packages (numpy, pandas, scipy, ...) install "
            "them first with `pip install --quiet --no-cache-dir <pkgs>` "
            "via run_shell.\n"
            "\n"
            "CRITICAL: run_python uses `python -c` — it does NOT echo the "
            "last expression like Jupyter or the REPL. Code like `x, y` "
            "on the last line evaluates but produces NO output. To see "
            "ANY value, you MUST call print(...). If a tool call returns "
            "empty stdout, your code didn't print — wrap your result in "
            "print() rather than retrying the same code.\n"
            "\n"
            "Tools:\n"
            "- run_python(code): runs Python source in a fresh interpreter. "
            "Imports/variables do NOT persist between calls, but files "
            "written to /tmp and installed packages DO persist.\n"
            "- run_shell(command): runs a shell command (bash -c).\n"
            "- list_files(path): lists a directory.\n"
            "- read_file(path): reads a file as text.\n"
            "\n"
            "Solve each subtask in as few tool calls as possible. Compose "
            "the full computation into one print()ed script when you can."
        ),
    )

    @agent.tool
    def run_python(ctx: RunContext[AgentDeps], code: str) -> CodeResult:
        """Executes Python source via ``python -c`` in the sandbox.

        IMPORTANT: this is NOT a REPL or a Jupyter cell. The last
        expression of ``code`` is NOT auto-displayed. You MUST call
        ``print(...)`` explicitly to see ANY output. Empty stdout
        almost always means missing print(), not a failed run.

        Args:
            ctx: PydanticAI run context, carrying the live SandboxSession.
            code: Self-contained Python source. Each call is a fresh
                interpreter; ``/tmp`` files and installed packages
                persist across calls.

        Returns:
            Captured stdout, stderr, and exit code.
        """
        # ``-u`` forces unbuffered output so prints arrive on the stream
        # immediately -- important so the step log shows progress live.
        return _exec_collect(ctx.deps.session, ["python", "-u", "-c", code])

    @agent.tool
    def run_shell(ctx: RunContext[AgentDeps], command: str) -> CodeResult:
        """Executes a shell command in the sandbox.

        Args:
            ctx: PydanticAI run context.
            command: Shell command to run via ``bash -c``.

        Returns:
            Captured stdout, stderr, and exit code.
        """
        return _exec_collect(ctx.deps.session, ["bash", "-lc", command])

    @agent.tool
    def list_files(ctx: RunContext[AgentDeps], path: str) -> CodeResult:
        """Lists a directory in the sandbox.

        Args:
            ctx: PydanticAI run context.
            path: Directory path to list.

        Returns:
            ``ls -la`` output as stdout.
        """
        return _exec_collect(ctx.deps.session, ["ls", "-la", "--", path])

    @agent.tool
    def read_file(ctx: RunContext[AgentDeps], path: str) -> CodeResult:
        """Reads a text file from the sandbox.

        Args:
            ctx: PydanticAI run context.
            path: File path inside the sandbox.

        Returns:
            File contents on stdout (capped at ``_MAX_STREAM_CHARS``).
        """
        # ``cat -- path`` so paths starting with - don't get parsed as flags.
        return _exec_collect(
            ctx.deps.session, ["bash", "-lc", f"cat -- {shlex.quote(path)}"]
        )

    return agent


_DEFAULT_QUERY = (
    "Benchmark three classic numerical-methods problems and report "
    "the answer plus how it compares to the known exact value:\n"
    "1. Estimate π using Monte Carlo with at least 200k samples.\n"
    "2. Approximate the integral of sin(x) from 0 to π using "
    "Simpson's rule with 1000 sub-intervals.\n"
    "3. Find a real root of x^2 - 612 using Newton's method starting "
    "at x0 = 25.\n"
    "Treat each problem as independent — no shared inputs, no shared "
    "files. For each, write a single self-contained Python script "
    "that print()s the result, run it once, and report the numerical "
    "answer with a one-line verification."
)


class _Subtasks(BaseModel):
    """Structured planner output."""

    subtasks: list[str]


def plan_subtasks(query: str, n: int = 3) -> list[str]:
    """Decomposes a user goal into ``n`` independent subtasks.

    Each subtask is meant to be tackled by an isolated subagent in its
    own sandbox session — no shared state, no cross-subagent
    dependencies. Used by the pipeline's planner step before fanning
    out via ``.map()``.

    Args:
        query: The user's natural-language goal.
        n: How many subtasks to produce.

    Returns:
        A list of self-contained subtask descriptions.
    """
    planner: Agent[None, _Subtasks] = Agent(
        "openai:gpt-4o-mini",
        output_type=_Subtasks,
        system_prompt=(
            f"Decompose the user's task into exactly {n} fully "
            "independent subtasks for parallel execution. CRITICAL: "
            "each subtask runs in its OWN isolated sandbox with a "
            "separate filesystem -- subtasks cannot read each other's "
            "files, share memory, or depend on each other's outputs. "
            "If the task involves shared data, each subtask must "
            "regenerate or re-derive its own copy. Each subtask "
            "should be self-contained, tractable by a Python "
            "data-analysis agent in under a minute, and produce a "
            "standalone result the parent can stitch together. "
            "Phrase each as a direct instruction."
        ),
    )
    return planner.run_sync(query).output.subtasks


def synthesize(query: str, parts: list[str]) -> str:
    """Aggregates per-subagent answers into one coherent response.

    Args:
        query: The original user goal.
        parts: The per-subtask answers produced by fanned-out subagents.

    Returns:
        A final natural-language response.
    """
    reducer: Agent[None, str] = Agent(
        "openai:gpt-4o-mini",
        system_prompt=(
            "You are synthesizing the answers of several subagents that "
            "each tackled an independent subtask of the user's "
            "original goal. Produce a single concise response that "
            "directly answers the original goal. Cite which subagent "
            "produced which finding when relevant."
        ),
    )
    bundle = f"Original goal: {query}\n\n" + "\n\n".join(
        f"Subagent {i + 1} result:\n{p}" for i, p in enumerate(parts)
    )
    return reducer.run_sync(bundle).output


def run_agent_in_session(session: SandboxSession, query: str) -> str:
    """Runs the agent loop against a caller-provided live session.

    Used by the fan-out pipeline so each subagent step can drive the
    agent against a session restored from a shared snapshot (avoids
    re-installing scientific deps in every fanned-out sandbox).

    Args:
        session: A live ``SandboxSession``. Must already be opened as
            a context manager so metadata + log forwarding fire.
        query: Natural-language task for the agent.

    Returns:
        The agent's final natural-language answer.
    """
    agent = build_agent()
    result = agent.run_sync(
        query,
        deps=AgentDeps(session=session),
        # PydanticAI defaults to 50 LLM requests per run; a multi-step
        # tool-using agent can chew through that on a rough day
        # (retries, package installs, etc.). Lift the cap so the
        # example doesn't UsageLimitExceeded prematurely.
        usage_limits=UsageLimits(request_limit=200),
    )
    return result.output


def run_agent(query: str = _DEFAULT_QUERY) -> str:
    """Drives the agent against a fresh session on the active stack's Sandbox.

    Opens a ``with`` block around a freshly-created Session. The
    Session base class handles step-metadata publishing and routes
    sandbox stdout/stderr into the step log stream when log forwarding
    is enabled.

    Args:
        query: Natural-language task for the agent.

    Returns:
        The agent's final natural-language answer.

    Raises:
        RuntimeError: If the active stack has no Sandbox component.
    """
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError(
            "No Sandbox component in the active stack. Register one "
            "(e.g. `zenml sandbox register modal-sb --flavor=modal`) "
            "and attach it via `zenml stack update --sandbox modal-sb`."
        )
    with sandbox.create_session() as session:
        return run_agent_in_session(session, query)
