"""ZenML Pipeline for OpenAI Agents SDK.

This pipeline demonstrates how to integrate OpenAI Agents SDK with ZenML
for orchestration and artifact management.
"""

from typing import Annotated, Any, Dict

from openai_agent import agent

from zenml import ExternalArtifact, pipeline, step


@step
def run_openai_agent(query: str) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the OpenAI Agents SDK agent and return results."""
    try:
        import agents

        # Use the default agent runner to execute the agent
        runner = agents.run.DEFAULT_AGENT_RUNNER
        result = runner.run_sync(agent, query)

        # Extract the final output
        response = result.final_output

        return {"query": query, "response": response, "status": "success"}
    except Exception as e:
        return {
            "query": query,
            "response": f"Agent error: {str(e)}",
            "status": "error",
        }


@step
def format_openai_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the OpenAI Agents SDK results into a readable summary."""
    query = agent_data["query"]
    response = agent_data["response"]
    status = agent_data["status"]

    if status == "error":
        formatted = f"""❌ OPENAI AGENTS SDK ERROR
{"=" * 40}

Query: {query}
Error: {response}
"""
    else:
        formatted = f"""🤖 OPENAI AGENTS SDK RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by OpenAI Agents SDK (Tools + GPT)
"""

    return formatted.strip()


@pipeline
def openai_agent_pipeline() -> str:
    """ZenML pipeline that orchestrates the OpenAI Agents SDK.

    Returns:
        Formatted agent response
    """
    # External artifact for agent query
    agent_query = ExternalArtifact(value="Tell me a fun fact about Tokyo")

    # Run the OpenAI Agents SDK agent
    agent_results = run_openai_agent(agent_query)

    # Format the results
    summary = format_openai_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running OpenAI Agents SDK pipeline...")
    run_result = openai_agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
