"""ZenML Pipeline for Haystack RAG System.

This pipeline demonstrates how to integrate Haystack RAG pipelines with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Dict

from haystack_agent import pipeline as haystack_pipeline

from zenml import pipeline, step
from zenml.config import DockerSettings, PythonPackageInstaller

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",  # relative to the pipeline directory
    environment={
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        # Set home directory to a writable location for Haystack storage
        "HOME": "/tmp",  # nosec B108 - Docker env var, not insecure file operation
        # Override Haystack-specific environment variables
        "HAYSTACK_CONTENT_TRACING_ENABLED": "false",
        "HAYSTACK_TELEMETRY_ENABLED": "false",
    },
)


@step
def run_haystack_rag(
    question: str,
) -> Annotated[Dict[str, str], "rag_results"]:
    """Execute the Haystack RAG pipeline and return its answer.

    Args:
        question: Question to answer using the in-memory documents.

    Returns:
        The original question and the generated answer.

    Raises:
        RuntimeError: If the Haystack pipeline returns no usable answer.
    """
    result = haystack_pipeline.run(
        {
            "retriever": {"query": question},
            "prompt_builder": {"question": question},
        },
        include_outputs_from={"llm"},
    )

    replies = result.get("llm", {}).get("replies", [])
    if not replies:
        raise RuntimeError("Haystack pipeline returned no replies.")

    answer = replies[0].text
    if not answer or not answer.strip():
        raise RuntimeError("Haystack pipeline returned an empty answer.")

    return {"question": question, "answer": answer}


@step
def format_rag_response(
    rag_data: Dict[str, str],
) -> Annotated[str, "formatted_response"]:
    """Format the Haystack RAG results into a readable summary.

    Args:
        rag_data: Question and generated answer to format.

    Returns:
        A readable summary of the RAG response.
    """
    question = rag_data["question"]
    answer = rag_data["answer"]

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

    Args:
        question: Question to answer using the in-memory documents.

    Returns:
        Formatted RAG response.
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
