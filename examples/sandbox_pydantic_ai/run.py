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
"""ZenML pipeline driving the PydanticAI + Sandbox agent.

Reads the active stack's Sandbox component, lets the PydanticAI agent
loop with a ``run_python`` tool that executes its generated code in the
sandbox, and returns the natural-language answer.
"""

from typing import Annotated

from agent import run_agent

from zenml import pipeline, step


@step
def agent_step(query: str) -> Annotated[str, "agent_answer"]:
    """Runs the PydanticAI agent against the active stack's Sandbox.

    Args:
        query: The natural-language question.

    Returns:
        The agent's answer.
    """
    return run_agent(query)


@pipeline(enable_cache=False)
def sandbox_pydantic_ai_pipeline(
    query: str = (
        "What's the sum of the first 100 prime numbers? "
        "Write Python to compute it."
    ),
) -> str:
    """Single-step pipeline that drives the PydanticAI agent."""
    return agent_step(query=query)


if __name__ == "__main__":
    print("Running PydanticAI + Sandbox pipeline...")
    sandbox_pydantic_ai_pipeline()
    print("Done. Check the ZenML dashboard for the run + log stream.")
