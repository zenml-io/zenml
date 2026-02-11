# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""RLM document analysis pipeline using ZenML dynamic pipelines.

Demonstrates the Reasoning Language Model (RLM) pattern applied to
email corpus analysis. The pipeline dynamically decomposes a research
query into parallel chunk analyses, each using a constrained multi-step
reasoning loop, then synthesizes findings into a final report.

DAG shape (determined at runtime):
    load_documents
         │
    plan_decomposition
         │
    ┌────┼────┬────┐
    │    │    │    │
   pc_0 pc_1 pc_2 pc_N     ← dynamic fan-out
    │    │    │    │
    └────┼────┴────┘
         │
    aggregate_results → report
"""

import os
from typing import Annotated, Any, Dict, List, Tuple

from steps import (
    aggregate_results,
    load_documents,
    plan_decomposition,
    process_chunk,
)

from zenml import pipeline
from zenml.config import DockerSettings, PythonPackageInstaller
from zenml.types import HTMLString

# --- Docker settings (pass API keys to container at compile time) ---
_docker_env: Dict[str, str] = {}
if os.getenv("OPENAI_API_KEY"):
    _docker_env["OPENAI_API_KEY"] = "${OPENAI_API_KEY}"
if os.getenv("LLM_MODEL"):
    _docker_env["LLM_MODEL"] = "${LLM_MODEL}"

_docker_kwargs: Dict[str, Any] = {
    "python_package_installer": PythonPackageInstaller.UV,
    "requirements": "requirements.txt",
}
if _docker_env:
    _docker_kwargs["environment"] = _docker_env

docker_settings = DockerSettings(**_docker_kwargs)


@pipeline(
    dynamic=True,
    enable_cache=True,
    settings={"docker": docker_settings},
)
def rlm_analysis_pipeline(
    source_path: str = "data/sample_emails.json",
    query: str = "What financial irregularities or concerns are discussed?",
    max_chunks: int = 4,
    max_iterations: int = 6,
) -> Tuple[
    Annotated[Dict[str, Any], "analysis_results"],
    Annotated[HTMLString, "report"],
]:
    """Analyze an email corpus using the RLM pattern with dynamic fan-out.

    1. Load emails and build a corpus summary
    2. Use LLM to decompose the query into chunk-level sub-queries
    3. Fan out N process_chunk steps (determined at runtime)
    4. Each chunk runs a constrained RLM loop (preview → plan → search → summarize)
    5. Aggregate all findings into a synthesis + HTML report

    Args:
        source_path: Path to JSON file containing email data.
        query: Research question to investigate across the corpus.
        max_chunks: Maximum parallel chunks (1-10). Controls DAG width.
        max_iterations: Max LLM calls per chunk (2-12). Controls step depth.

    Returns:
        Tuple of (structured analysis results, HTML report).
    """
    # Clamp budgets to prevent resource exhaustion
    max_chunks = min(max(max_chunks, 1), 10)
    max_iterations = min(max(max_iterations, 2), 12)

    # Step 1: Load and summarize the corpus
    documents, doc_summary = load_documents(source_path=source_path)

    # Step 2: Decompose into chunk specs
    chunk_specs = plan_decomposition(
        doc_summary=doc_summary,
        query=query,
        max_chunks=max_chunks,
    )

    # Step 3: Dynamic fan-out — create one process_chunk step per chunk
    # Each invocation gets a unique step name automatically in the DAG.
    process_step = process_chunk.with_options(
        parameters={"query": query, "max_iterations": max_iterations}
    )

    chunk_specs_data = chunk_specs.load()
    chunk_results: List[Any] = []
    for idx in range(len(chunk_specs_data)):
        result, _trajectory = process_step(
            documents=documents,
            chunk_spec=chunk_specs.chunk(index=idx),
        )
        chunk_results.append(result)

    # Step 4: Synthesize all chunk findings
    return aggregate_results(
        chunk_results=chunk_results,
        query=query,
    )
