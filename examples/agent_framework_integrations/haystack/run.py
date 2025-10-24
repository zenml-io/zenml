"""ZenML Pipeline for Haystack RAG System.

This pipeline demonstrates how to integrate Haystack RAG pipelines with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from haystack_agent import pipeline as haystack_pipeline

from zenml import pipeline, step
from zenml.config import DockerSettings, PythonPackageInstaller

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",  # relative to the pipeline directory
    environment={
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    },
)


@step
def run_haystack_rag(
    question: str,
) -> Annotated[Dict[str, Any], "rag_results"]:
    """Execute the Haystack RAG pipeline and return results."""
    try:
        result = haystack_pipeline.run(
            {
                "retriever": {"query": question},
                "prompt_builder": {"question": question},
            },
            include_outputs_from={"llm"},
        )

        # Extract the response from the nested structure
        if (
            "llm" in result
            and "replies" in result["llm"]
            and result["llm"]["replies"]
        ):
            response = result["llm"]["replies"][
                0
            ]  # Already a string in newer Haystack versions
        else:
            response = "No response generated"

        return {"question": question, "answer": response, "status": "success"}
    except Exception as e:
        return {
            "question": question,
            "answer": f"RAG error: {str(e)}",
            "status": "error",
        }


@step
def format_rag_response(
    rag_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the Haystack RAG results into a readable summary."""
    question = rag_data["question"]
    answer = rag_data["answer"]
    status = rag_data["status"]

    if status == "error":
        formatted = f"""❌ HAYSTACK RAG ERROR
{"=" * 40}

Question: {question}
Error: {answer}
"""
    else:
        formatted = f"""🔍 HAYSTACK RAG RESPONSE
{"=" * 40}

Question: {question}

Answer:
{answer}

🤖 Powered by Haystack RAG (BM25 + OpenAI)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def agent_pipeline(
    question: str = "What city is home to the Eiffel Tower?",
) -> str:
    """ZenML pipeline that orchestrates the Haystack RAG system.

    Returns:
        Formatted RAG response
    """
    # Run the Haystack RAG pipeline
    rag_results = run_haystack_rag(question=question)

    # Format the results
    summary = format_rag_response(rag_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running Haystack RAG pipeline...")
    run_result = agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
