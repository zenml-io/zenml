"""ZenML Pipeline for LangGraph ReAct Agent.

This pipeline demonstrates how to integrate LangGraph agents with ZenML
for orchestration and artifact management.
"""

from typing import Annotated, Any, Dict

from langgraph_agent import agent

from zenml import ExternalArtifact, pipeline, step


@step
def run_langgraph_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the LangGraph ReAct agent and return results."""
    try:
        # LangGraph agents expect messages in a specific format
        messages = [{"role": "user", "content": query}]
        result = agent.invoke({"messages": messages})

        # Extract the response from the result
        if "messages" in result and result["messages"]:
            # Get the last message (assistant's response)
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                response = last_message.content
            else:
                response = str(last_message)
        else:
            response = str(result)

        return {"query": query, "response": response, "status": "success"}
    except Exception as e:
        return {
            "query": query,
            "response": f"Agent error: {str(e)}",
            "status": "error",
        }


@step
def format_langgraph_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the LangGraph agent results into a readable summary."""
    query = agent_data["query"]
    response = agent_data["response"]
    status = agent_data["status"]

    if status == "error":
        formatted = f"""❌ LANGGRAPH AGENT ERROR
{"=" * 40}

Query: {query}
Error: {response}
"""
    else:
        formatted = f"""🤖 LANGGRAPH REACT AGENT RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by LangGraph (ReAct Agent + Tools)
"""

    return formatted.strip()


@pipeline
def langgraph_agent_pipeline() -> str:
    """ZenML pipeline that orchestrates the LangGraph ReAct agent.

    Returns:
        Formatted agent response
    """
    # External artifact for agent query
    agent_query = ExternalArtifact(
        value="What is the weather in San Francisco?"
    )

    # Run the LangGraph agent
    agent_results = run_langgraph_agent(agent_query)

    # Format the results
    summary = format_langgraph_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running LangGraph ReAct agent pipeline...")
    run_result = langgraph_agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
