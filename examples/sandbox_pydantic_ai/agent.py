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
"""PydanticAI agent with a ZenML Sandbox-backed code-execution tool.

The agent has one tool, ``run_python``, that takes a Python source string,
executes it inside the active stack's Sandbox, and returns stdout + exit
code. The Sandbox isolates the LLM-generated code from the agent process,
which is the headline use case for the Sandbox stack component.
"""

from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from zenml.client import Client
from zenml.sandboxes import SandboxSession

# Cap the stdout/stderr surface the agent sees per tool call. Passed to
# ``SandboxProcess.collect`` as ``max_chars`` -- the base helper drains
# both streams fully (so the provider's wait() doesn't block on a
# buffered reader) and flags per-stream truncation via ``SandboxOutput``.
_MAX_STREAM_CHARS = 32_000


class CodeResult(BaseModel):
    """Structured result returned by the ``run_python`` tool."""

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


def build_agent() -> Agent[AgentDeps, str]:
    """Constructs the PydanticAI agent with the sandbox tool registered.

    Returns:
        A PydanticAI ``Agent`` that runs Python code through the active
        ZenML stack's Sandbox via a single ``run_python`` tool.
    """
    agent: Agent[AgentDeps, str] = Agent(
        "openai:gpt-4o-mini",
        deps_type=AgentDeps,
        system_prompt=(
            "You are a data-analysis assistant. To answer questions that "
            "need computation, write Python code and call the run_python "
            "tool with it. Each call is a fresh Python interpreter -- "
            "imports and variables do NOT persist between calls, so write "
            "self-contained scripts. Files written under /tmp do persist. "
            "Print the final answer to stdout."
        ),
    )

    @agent.tool
    def run_python(ctx: RunContext[AgentDeps], code: str) -> CodeResult:
        """Executes Python code in the sandbox.

        Args:
            ctx: PydanticAI run context, carrying the live SandboxSession.
            code: Python source to execute. Must be self-contained.

        Returns:
            The captured stdout, stderr, and exit code.
        """
        # ``-u`` forces unbuffered output so prints arrive on the stream
        # immediately -- important once the Modal flavor's log-forwarding
        # wraps these iterators (lines surface in the step log live).
        process = ctx.deps.session.exec(["python", "-u", "-c", code])
        # ``collect`` drains both streams to completion (so the
        # provider's wait() is safe), caps each stream at max_chars,
        # and flags truncation per-stream. Replaces the three-line
        # ``stdout = _drain(...); stderr = _drain(...); wait()`` dance.
        out = process.collect(max_chars=_MAX_STREAM_CHARS)
        # ``SandboxOutput`` is frozen; assemble the truncation-marker
        # strings locally and pass them on rather than mutating in place.
        stdout = out.stdout
        if out.stdout_truncated:
            stdout += (
                f"\n... [stdout truncated at {_MAX_STREAM_CHARS} chars]\n"
            )
        stderr = out.stderr
        if out.stderr_truncated:
            stderr += (
                f"\n... [stderr truncated at {_MAX_STREAM_CHARS} chars]\n"
            )
        return CodeResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=out.exit_code,
        )

    return agent


def run_agent(query: str) -> str:
    """Drives the agent against the active stack's Sandbox.

    Opens a ``with`` block around the Session. When the flavor enables
    log forwarding (e.g. Modal opens a ``LoggingContext`` on
    ``__enter__`` when ``forward_logs_to_step`` resolves True), sandbox
    stdout/stderr surfaces in the step's log stream as a dedicated
    ``sandbox:<session_id>`` source. The Modal flavor also records the
    sandbox session id and dashboard URL as step metadata on
    ``__enter__`` -- both behaviors only fire inside a ``with`` block.

    Args:
        query: The natural-language question to ask the agent.

    Returns:
        The agent's final natural-language answer.

    Raises:
        RuntimeError: If the active stack does not have a Sandbox
            component configured.
    """
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError(
            "No Sandbox component in the active stack. Register one "
            "(e.g. `zenml sandbox register modal-sb --flavor=modal`) "
            "and attach it via `zenml stack update --sandbox modal-sb`."
        )

    agent = build_agent()
    with sandbox.create_session() as session:
        result = agent.run_sync(query, deps=AgentDeps(session=session))
    return result.output
