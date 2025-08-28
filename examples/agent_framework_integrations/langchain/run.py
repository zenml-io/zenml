"""ZenML Pipeline for LangChain Document Summarization.

This pipeline demonstrates how to integrate LangChain chains with ZenML
for orchestration and artifact management.
"""

from typing import Annotated, Any, Dict

from langchain_agent import chain

from zenml import ExternalArtifact, pipeline, step


@step
def run_langchain_chain(
    url_input: str,
) -> Annotated[Dict[str, Any], "chain_results"]:
    """Execute the LangChain chain for document summarization."""
    try:
        # Extract URL from input (assuming format "Summarize: URL")
        if ":" in url_input and url_input.startswith("Summarize"):
            url = url_input.split(":", 1)[1].strip()
        else:
            url = url_input  # Fallback to use input as URL directly

        # Execute the LangChain chain
        result = chain.invoke({"url": url})

        return {"url": url, "summary": result, "status": "success"}
    except Exception as e:
        return {
            "url": url_input,
            "summary": f"Chain error: {str(e)}",
            "status": "error",
        }


@step
def format_langchain_response(
    chain_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the LangChain results into a readable summary."""
    url = chain_data["url"]
    summary = chain_data["summary"]
    status = chain_data["status"]

    if status == "error":
        formatted = f"""❌ LANGCHAIN CHAIN ERROR
{"=" * 40}

URL: {url}
Error: {summary}
"""
    else:
        formatted = f"""📄 LANGCHAIN DOCUMENT SUMMARY
{"=" * 40}

Source: {url}

Summary:
{summary}

🦜 Powered by LangChain (WebLoader + OpenAI)
"""

    return formatted.strip()


@pipeline
def langchain_summarization_pipeline() -> str:
    """ZenML pipeline that orchestrates the LangChain document summarization.

    Returns:
        Formatted document summary
    """
    # External artifact for URL to summarize
    document_url = ExternalArtifact(
        value="Summarize: https://python.langchain.com/docs/introduction/"
    )

    # Run the LangChain chain
    chain_results = run_langchain_chain(document_url)

    # Format the results
    summary = format_langchain_response(chain_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running LangChain summarization pipeline...")
    run_result = langchain_summarization_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
