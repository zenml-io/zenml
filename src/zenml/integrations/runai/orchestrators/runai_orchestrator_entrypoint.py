#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Entrypoint for Run:AI orchestrator workload.

This module is executed inside Run:AI training workloads and runs the pipeline
steps sequentially in a single container (MVP implementation).
"""

import argparse
import os
import sys
from typing import TYPE_CHECKING

from zenml.client import Client
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import PipelineRunUpdate
from zenml.pipelines.run_utils import create_placeholder_run

if TYPE_CHECKING:
    from zenml.models import PipelineSnapshotResponse

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot_id", type=str, required=True)
    parser.add_argument("--run_id", type=str, required=False)
    return parser.parse_args()


def main() -> None:
    """Entrypoint for Run:AI orchestrator workload.

    This function:
    1. Loads the pipeline snapshot
    2. Downloads user code if needed
    3. Activates integrations
    4. Runs each pipeline step sequentially
    """
    logger.info("Run:AI orchestrator workload started")

    args = parse_args()

    client = Client()
    snapshot = client.get_snapshot(args.snapshot_id)

    # Download code from artifact store or code repository if needed
    # This must happen before any step code is imported
    _download_code_if_needed(snapshot)

    integration_registry.activate_integrations()

    from zenml.integrations.runai.orchestrators.runai_orchestrator import (
        ENV_ZENML_RUNAI_WORKLOAD_ID,
    )

    orchestrator_run_id = os.environ.get(ENV_ZENML_RUNAI_WORKLOAD_ID)
    if not orchestrator_run_id:
        logger.warning(
            "No Run:AI workload ID found in environment, using fallback"
        )
        orchestrator_run_id = f"runai-{args.snapshot_id}"

    if args.run_id:
        logger.info(f"Updating existing pipeline run: {args.run_id}")
        pipeline_run = client.zen_store.update_run(
            run_id=args.run_id,
            run_update=PipelineRunUpdate(
                orchestrator_run_id=orchestrator_run_id
            ),
        )
    else:
        logger.info("Creating placeholder pipeline run")
        pipeline_run = create_placeholder_run(
            snapshot=snapshot,
            orchestrator_run_id=orchestrator_run_id,
        )

    logger.info(
        f"Running pipeline '{snapshot.pipeline_configuration.name}' "
        f"(run_id={pipeline_run.id})"
    )

    orchestrator = client.active_stack.orchestrator

    orchestrator._prepare_run(snapshot=snapshot)

    for step_name, step_config in snapshot.step_configurations.items():
        logger.info(f"Running step: {step_name}")
        try:
            orchestrator.run_step(step_config)
            logger.info(f"Step '{step_name}' completed successfully")
        except Exception as e:
            logger.error(f"Step '{step_name}' failed: {e}")
            raise

    logger.info("Run:AI orchestrator workload completed")


def _download_code_if_needed(snapshot: "PipelineSnapshotResponse") -> None:
    """Download code from artifact store or code repository if needed.

    Args:
        snapshot: The pipeline snapshot.
    """
    from zenml.utils import code_utils

    # Check if code needs to be downloaded
    if snapshot.code_path:
        logger.info("Downloading code from artifact store...")
        artifact_store = Client().active_stack.artifact_store
        code_utils.download_code_from_artifact_store(
            code_path=snapshot.code_path,
            artifact_store=artifact_store,
        )
        logger.info("Code download from artifact store completed")
    elif snapshot.code_reference:
        logger.info(
            "Downloading code from code repository '%s' (commit '%s')...",
            snapshot.code_reference.code_repository.name,
            snapshot.code_reference.commit,
        )
        from zenml.code_repositories import BaseCodeRepository

        model = Client().get_code_repository(
            snapshot.code_reference.code_repository.id
        )
        repo = BaseCodeRepository.from_model(model)
        code_repo_root = os.path.abspath("code")
        download_dir = os.path.join(
            code_repo_root, snapshot.code_reference.subdirectory
        )
        os.makedirs(download_dir, exist_ok=True)
        repo.download_files(
            commit=snapshot.code_reference.commit,
            directory=code_repo_root,
            repo_sub_directory=snapshot.code_reference.subdirectory,
        )

        from zenml.utils import source_utils

        source_utils.set_custom_source_root(download_dir)
        sys.path.insert(0, download_dir)
        os.chdir(download_dir)
        logger.info("Code download from code repository completed")
    else:
        # Code is included in the image, make sure cwd is in sys.path
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        logger.info("Using code included in the container image")


if __name__ == "__main__":
    main()
