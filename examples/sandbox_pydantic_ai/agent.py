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

from typing import List

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from zenml.client import Client
from zenml.sandboxes import SandboxSession


class CodeResult(BaseModel):
    """Structured result returned by the ``run_python`` tool."""

    stdout: str
    stderr: str
    exit_code: int


class AgentDeps(BaseModel):
    """Dependencies injected into every tool call.

    Carries the live ``SandboxSession`` so all tool invocations share one
    interpreter state (filesystem persists between calls).
    """

    model_config = {"arbitrary_types_allowed": True}
    session: SandboxSession


def _drain(stream: List[str], limit: int = 500) -> str:
    """Reads up to ``limit`` lines from a SandboxProcess stream iterator.

    Bounded so a runaway agent doesn't hang the pipeline.
    """
    lines: List[str] = []
    for _ in range(limit):
        try:
            lines.append(next(stream))
        except StopIteration:
            break
    return "".join(lines)


def build_agent() -> Agent[AgentDeps, str]:
    """Constructs the PydanticAI agent with the sandbox tool registered.

    Returns:
        A PydanticAI ``Agent`` that streams Python code execution through
        the active ZenML stack's Sandbox.
    """
    agent: Agent[AgentDeps, str] = Agent(
        "openai:gpt-4o-mini",
        deps_type=AgentDeps,
        system_prompt=(
            "You are a data-analysis assistant. To answer questions that "
            "need computation, write Python code and call the run_python "
            "tool with it. The tool executes the code in an isolated "
            "sandbox and returns stdout, stderr, and the exit code. Keep "
            "code self-contained and print the final answer."
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
        process = ctx.deps.session.exec(["python", "-c", code])
        stdout = _drain(process.stdout())
        stderr = _drain(process.stderr())
        exit_code = process.wait()
        return CodeResult(stdout=stdout, stderr=stderr, exit_code=exit_code)

    return agent


def run_agent(query: str) -> str:
    """Drives the agent against the active stack's Sandbox.

    Opens a ``with`` block around the Session so log forwarding (if the
    flavor enables it) routes sandbox stdout/stderr into ZenML's step
    log stream as a per-session source.

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
