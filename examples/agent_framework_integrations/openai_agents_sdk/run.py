"""ZenML Pipeline for OpenAI Agents SDK.

This pipeline demonstrates how to integrate OpenAI Agents SDK with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from zenml import pipeline, step
from zenml.config import (
    DeploymentSettings,
    DockerSettings,
    SecureHeadersConfig,
)

deploy_settings = DeploymentSettings(
    app_title="Travel Assistant",
    app_description=(
        "A travel assistant that can provide weather information and general facts about cities around the world."
    ),
    app_version="0.1",
    dashboard_files_path="ui",
    secure_headers=SecureHeadersConfig(
        csp=(
            "default-src 'none'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "connect-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'"
        ),
    ),
)

docker_settings = DockerSettings(
    requirements="requirements.txt",  # relative to the pipeline directory
    environment={
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    },
)


@step
def run_openai_agent(query: str) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the OpenAI Agents SDK agent and return results.

    Args:
        query: Question for the agent.

    Returns:
        The query and generated response.

    Raises:
        RuntimeError: If the agent subprocess fails.
    """
    import json
    import subprocess
    import sys
    import tempfile

    # Create a standalone script to run the agent in a separate process
    agent_script = '''
import asyncio
import sys
import json
import os

# Add current directory to path to find openai_agent module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai_agent import agent
from agents import Runner

async def run_agent(query):
    """Run the agent asynchronously."""
    result = await Runner.run(agent, query)
    return result.final_output

def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Hello"

    # Create new event loop for this process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        response = loop.run_until_complete(run_agent(query))
        print(json.dumps({"response": response}))
    finally:
        loop.close()

if __name__ == "__main__":
    main()
'''

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False
    ) as f:
        f.write(agent_script)
        script_path = f.name

    try:
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        work_dir = (
            "/app/code" if os.path.exists("/app/code") else current_file_dir
        )

        result = subprocess.run(
            [sys.executable, script_path, query],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=work_dir,
            env={**os.environ, "PYTHONPATH": work_dir},
        )
        if result.returncode != 0:
            error = result.stderr.strip() or "OpenAI agent subprocess failed."
            raise RuntimeError(error)

        output_data = json.loads(result.stdout.strip())
        return {
            "query": query,
            "response": output_data["response"],
        }
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


@step
def format_openai_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the OpenAI Agents SDK results into a readable summary.

    Args:
        agent_data: Query and generated response.

    Returns:
        The formatted agent response.
    """
    query = agent_data["query"]
    response = agent_data["response"]
    formatted = f"""🤖 OPENAI AGENTS SDK RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by OpenAI Agents SDK (Tools + GPT)
"""

    return formatted.strip()


@pipeline(
    settings={
        "docker": docker_settings,
        "deployment": deploy_settings,
    },
    enable_cache=False,
)
def agent_pipeline(query: str = "Tell me a fun fact about Tokyo") -> str:
    """ZenML pipeline that orchestrates the OpenAI Agents SDK.

    Returns:
        Formatted agent response
    """
    # Run the OpenAI Agents SDK agent
    agent_results = run_openai_agent(query=query)

    # Format the results
    summary = format_openai_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running OpenAI Agents SDK pipeline...")
    run_result = agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
