#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Utilities for step logs."""

import os
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from zenml.artifact_stores.base_artifact_store_logging_handler import (
    ArtifactStoreLoggingHandler,
)
from zenml.io import fileio
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore


logger = get_logger(__name__)


def prepare_logs_uri(
    artifact_store: "BaseArtifactStore",
    pipeline_run_id: str,
    step_name: str,
    log_key: Optional[str] = str(uuid4()),
) -> str:
    """Generates and prepares a URI for the log file for a step.

    Args:
        artifact_store: The artifact store on which the artifact will be stored.
        pipeline_run_id: The id of the pipeline run.
        step_name: Name of the step.
        log_key: The name of the output in the step run for this artifact.

    Returns:
        The URI of the output artifact.
    """
    logs_uri = os.path.join(
        artifact_store.path,
        pipeline_run_id,
        step_name,
        f"logs-{log_key}",
    )

    # Create the file, it should not exist at this point
    if fileio.exists(logs_uri):
        raise RuntimeError("Logs file already exists")
    fileio.makedirs(logs_uri)
    return logs_uri


def get_step_logging_handler(
    artifact_store: "BaseArtifactStore",
    logs_uri: str,
    when: str = "s",
    interval: int = 1,
    backupCount: int = 0,
) -> ArtifactStoreLoggingHandler:
    """Sets up a logging handler for the artifact store.

    Args:
        artifact_store: The artifact store on which the artifact will be stored.
        logs_uri: The URI of the output artifact.
        when: The unit of time to wait between logging.
        interval: The interval of time to wait between logging.
        backupCount: The number of backups to keep.

    Returns:
        The logging handler.
    """
    return ArtifactStoreLoggingHandler(
        artifact_store,
        logs_uri,
        when="s",
        interval=1,
        backupCount=0,
    )
