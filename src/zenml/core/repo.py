#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""Base ZenML repository"""

import os
from typing import List, Optional

from git import InvalidGitRepositoryError  # type: ignore[attr-defined]

import zenml.io.utils
from zenml.core.constants import ZENML_DIR_NAME
from zenml.core.git_wrapper import GitWrapper
from zenml.core.local_service import LocalService
from zenml.exceptions import InitializationException
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.post_execution import PipelineView
from zenml.stacks import BaseStack
from zenml.utils.analytics_utils import (
    GET_PIPELINE,
    GET_PIPELINES,
    SET_STACK,
    track,
)

logger = get_logger(__name__)


class Repository:
    """ZenML repository definition.

    Every ZenML project exists inside a ZenML repository.
    """

    def __init__(self, path: Optional[str] = None):
        """
        Construct reference to a ZenML repository.

        Args:
            path (str): Path to root of repository
        """
        self.path = zenml.io.utils.get_zenml_dir(path)
        self.service = LocalService(repo_path=self.path)

        try:
            self.git_wrapper = GitWrapper(self.path)
        except InvalidGitRepositoryError:
            self.git_wrapper = None  # type: ignore[assignment]

    @staticmethod
    def init_repo(path: str = os.getcwd()) -> None:
        """Initializes a ZenML repository.

        Args:
            path: Path where the ZenML repository should be created.

        Raises:
            InitializationException: If a ZenML repository already exists at
                the given path.
        """
        if zenml.io.utils.is_zenml_dir(path):
            raise InitializationException(
                f"A ZenML repository already exists at path '{path}'."
            )

        # Create the base dir
        zen_dir = os.path.join(path, ZENML_DIR_NAME)
        fileio.create_dir_recursive_if_not_exists(zen_dir)

        from zenml.artifact_stores import LocalArtifactStore
        from zenml.metadata_stores import SQLiteMetadataStore
        from zenml.orchestrators import LocalOrchestrator

        service = LocalService(repo_path=path)

        artifact_store_path = os.path.join(
            zenml.io.utils.get_global_config_directory(),
            "local_stores",
            str(service.uuid),
        )
        metadata_store_path = os.path.join(artifact_store_path, "metadata.db")

        service.register_artifact_store(
            "local_artifact_store",
            LocalArtifactStore(path=artifact_store_path, repo_path=path),
        )

        service.register_metadata_store(
            "local_metadata_store",
            SQLiteMetadataStore(uri=metadata_store_path, repo_path=path),
        )

        service.register_orchestrator(
            "local_orchestrator", LocalOrchestrator(repo_path=path)
        )

        service.register_stack(
            "local_stack",
            BaseStack(
                metadata_store_name="local_metadata_store",
                artifact_store_name="local_artifact_store",
                orchestrator_name="local_orchestrator",
            ),
        )

        service.set_active_stack_key("local_stack")

    def get_git_wrapper(self) -> GitWrapper:
        """Returns the git wrapper for the repo."""
        return self.git_wrapper

    def get_service(self) -> LocalService:
        """Returns the active service. For now, always local."""
        return self.service

    @track(event=SET_STACK)
    def set_active_stack(self, stack_key: str) -> None:
        """Set the active stack for the repo. This change is local for the
        machine.

        Args:
            stack_key: Key of the stack to set active.
        """
        self.service.set_active_stack_key(stack_key)

    def get_active_stack_key(self) -> str:
        """Get the active stack key from global config.

        Returns:
            Currently active stacks key.
        """
        return self.service.get_active_stack_key()

    def get_active_stack(self) -> BaseStack:
        """Get the active stack from global config.

        Returns:
            Currently active stack.
        """
        return self.service.get_stack(self.get_active_stack_key())

    @track(event=GET_PIPELINES)
    def get_pipelines(
        self, stack_key: Optional[str] = None
    ) -> List[PipelineView]:
        """Returns a list of all pipelines.

        Args:
            stack_key: If specified, pipelines in the metadata store of the
                given stack are returned. Otherwise pipelines in the metadata
                store of the currently active stack are returned.
        """
        stack_key = stack_key or self.get_active_stack_key()
        metadata_store = self.service.get_stack(stack_key).metadata_store
        return metadata_store.get_pipelines()

    @track(event=GET_PIPELINE)
    def get_pipeline(
        self, pipeline_name: str, stack_key: Optional[str] = None
    ) -> Optional[PipelineView]:
        """Returns a pipeline for the given name or `None` if it doesn't exist.

        Args:
            pipeline_name: Name of the pipeline.
            stack_key: If specified, pipelines in the metadata store of the
                given stack are returned. Otherwise pipelines in the metadata
                store of the currently active stack are returned.
        """
        stack_key = stack_key or self.get_active_stack_key()
        metadata_store = self.service.get_stack(stack_key).metadata_store
        return metadata_store.get_pipeline(pipeline_name)

    def clean(self) -> None:
        """Deletes associated metadata store, pipelines dir and artifacts"""
        raise NotImplementedError
