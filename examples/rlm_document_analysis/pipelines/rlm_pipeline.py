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

Demonstrates the Recursive Language Model (RLM) pattern applied to
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

import json
import os
from pathlib import Path
from typing import Annotated, Any, Dict, List, Tuple
from uuid import UUID

from steps import (
    aggregate_results,
    load_documents,
    plan_decomposition,
    process_chunk,
)

from zenml import ExternalArtifact, pipeline
from zenml.config import (
    DeploymentSettings,
    DockerSettings,
    PythonPackageInstaller,
)
from zenml.types import HTMLString

BUNDLED_SAMPLE = "data/sample_emails.json"

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

deployment_settings = DeploymentSettings(
    app_title="RLM Document Analysis",
    app_description="Dynamic pipelines + Recursive Language Model (RLM) pattern",
    dashboard_files_path="ui",
)


def _resolve_data_file(source_path: str) -> Path:
    """Resolve a data file path, trying multiple locations.

    Used as a fallback when no pre-uploaded artifact is provided (e.g.,
    deployment via API/UI). Tries paths relative to this file, in Docker
    container locations, and as-is.

    Args:
        source_path: Path to data file (typically the bundled sample).

    Returns:
        Resolved Path object.

    Raises:
        FileNotFoundError: If no valid path is found.
    """
    candidates = [
        Path(source_path),
        Path(__file__).parent.parent / source_path,
        Path("/app") / source_path,
        Path("/app/code") / source_path,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Data file not found. Tried: {[str(c) for c in candidates]}. "
        f"Run setup_data.py to download the dataset, or use the bundled "
        f"sample at {BUNDLED_SAMPLE}."
    )


@pipeline(
    dynamic=True,
    enable_cache=True,
    settings={
        "docker": docker_settings,
        "deployment": deployment_settings,
    },
)
def rlm_analysis_pipeline(
    emails_artifact_id: str = "",
    query: str = "What financial irregularities or concerns are discussed?",
    max_chunks: int = 4,
    max_iterations: int = 6,
) -> Tuple[
    Annotated[Dict[str, Any], "analysis_results"],
    Annotated[HTMLString, "report"],
]:
    """Analyze an email corpus using the RLM pattern with dynamic fan-out.

    1. Load email data and pass to the first step via ExternalArtifact
    2. Build a corpus summary
    3. Use LLM to decompose the query into chunk-level sub-queries
    4. Fan out N process_chunk steps (determined at runtime)
    5. Each chunk runs a constrained RLM loop (preview → plan → search → summarize)
    6. Aggregate all findings into a synthesis + HTML report

    For remote orchestrators (Kubernetes, etc.), the data must be pre-uploaded
    to the artifact store by the caller (run.py does this via save_artifact)
    because this pipeline function executes inside the orchestrator pod, not
    on the client machine. The emails_artifact_id parameter references the
    pre-uploaded artifact.

    For deployments (invoked via API/UI) or when no artifact ID is provided,
    falls back to reading the bundled sample from the code archive.

    Args:
        emails_artifact_id: UUID of a pre-uploaded email corpus artifact.
            If empty, falls back to the bundled sample dataset.
        query: Research question to investigate across the corpus.
        max_chunks: Maximum parallel chunks (1-10). Controls DAG width.
        max_iterations: Max LLM calls per chunk (2-12). Controls step depth.

    Returns:
        Tuple of (structured analysis results, HTML report).
    """
    # Clamp budgets to prevent resource exhaustion
    max_chunks = min(max(max_chunks, 1), 10)
    max_iterations = min(max(max_iterations, 2), 12)

    # Resolve the email data as an artifact for the load_documents step.
    # When called from run.py: data was pre-uploaded via save_artifact(),
    # so we fetch the artifact version by ID (no file I/O needed in the pod).
    # When called from deployment API/UI: no artifact ID is provided,
    # so we read the bundled sample from the code archive.
    if emails_artifact_id:
        from zenml.client import Client

        emails_artifact = Client().get_artifact_version(
            UUID(emails_artifact_id)
        )
    else:
        data_path = _resolve_data_file(BUNDLED_SAMPLE)
        with open(data_path, encoding="utf-8") as f:
            emails_data = json.load(f)
        emails_artifact = ExternalArtifact(value=emails_data)

    # Step 1: Validate data and build corpus summary
    documents, doc_summary = load_documents(emails=emails_artifact)

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
    chunk_trajectories: List[Any] = []
    for idx in range(len(chunk_specs_data)):
        result, trajectory = process_step(
            documents=documents,
            chunk_spec=chunk_specs.chunk(index=idx),
        )
        chunk_results.append(result)
        chunk_trajectories.append(trajectory)

    # Step 4: Synthesize all chunk findings
    return aggregate_results(
        chunk_results=chunk_results,
        chunk_trajectories=chunk_trajectories,
        query=query,
    )
