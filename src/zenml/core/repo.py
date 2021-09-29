#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Base ZenML repository"""

import os
from typing import List, Optional, Text, Type, Union

from git import InvalidGitRepositoryError

from zenml.artifact_stores.local_artifact_store import LocalArtifactStore
from zenml.config.global_config import GlobalConfig
from zenml.core.constants import ZENML_DIR_NAME
from zenml.core.git_wrapper import GitWrapper
from zenml.core.local_service import LocalService
from zenml.exceptions import InitializationException
from zenml.logger import get_logger
from zenml.metadata.sqlite_metadata_wrapper import SQLiteMetadataStore
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.stacks.base_stack import BaseStack
from zenml.utils import path_utils
from zenml.utils.analytics_utils import (
    CREATE_REPO,
    GET_PIPELINES,
    GET_STEP_VERSION,
    GET_STEPS_VERSIONS,
    track,
)

logger = get_logger(__name__)


class Repository:
    """ZenML repository definition.

    Every ZenML project exists inside a ZenML repository.
    """

    def __init__(self, path: Text = None):
        """
        Construct reference a ZenML repository.

        Args:
            path (str): Path to root of repository
        """
        if path is None:
            try:
                # Start from cwd and traverse up until find zenml config.
                path = path_utils.get_zenml_dir(os.getcwd())
            except InitializationException:
                # If there isn't a zenml.config, use the cwd
                path = os.getcwd()

        if not path_utils.is_dir(path):
            raise FileNotFoundError(f"{path} does not exist or is not a dir!")
        self.path = path
        self.service = LocalService()

        # Hook up git, path needs to have a git folder.
        try:
            self.git_wrapper = GitWrapper(self.path)
        except InvalidGitRepositoryError:
            # We only need to raise exception in the `init_repo`, not in the
            #  constructor here. This makes it more relaxed in remote
            #  orchestration scenarios. We might want to revisit this.
            self.git_wrapper = None

    @staticmethod
    @track(event=CREATE_REPO)
    def init_repo(
        repo_path: Text = os.getcwd(),
        stack: BaseStack = None,
        analytics_opt_in: bool = None,
    ):
        """
        Initializes a git repo with zenml.

        Args:
            repo_path (str): path to root of a git repo
            stack: Initial stack.
            analytics_opt_in: opt-in flag for analytics code.

        Raises:
            InvalidGitRepositoryError: If repository is not a git repository.
            NoSuchPathError: If the repo_path does not exist.
        """
        # First check whether it already exists or not
        if path_utils.is_zenml_dir(repo_path):
            raise AssertionError(f"{repo_path} is already initialized!")

        # Edit global config
        gc = GlobalConfig()
        if analytics_opt_in is not None:
            gc.analytics_opt_in = analytics_opt_in
            gc.update()

        try:
            GitWrapper(repo_path)
        except InvalidGitRepositoryError:
            raise InitializationException(
                f"{repo_path} is not a valid git repository. Please initialize"
                f" the repository with `git init`."
            )

        # Create the base dir
        zen_dir = os.path.join(repo_path, ZENML_DIR_NAME)
        path_utils.create_dir_recursive_if_not_exists(zen_dir)

        # set up metadata and artifact store defaults
        artifact_dir = os.path.join(zen_dir, "local_store")
        metadata_dir = os.path.join(artifact_dir, "metadata.db")

        if stack is None:
            service = LocalService()

            service.register_artifact_store(
                "local_artifact_store", LocalArtifactStore(path=artifact_dir)
            )

            service.register_metadata_store(
                "local_metadata_store", SQLiteMetadataStore(uri=metadata_dir)
            )

            service.register_orchestrator(
                "local_orchestrator", LocalOrchestrator()
            )

            service.register_stack(
                "local_stack",
                BaseStack(
                    metadata_store_name="local_metadata_store",
                    artifact_store_name="local_artifact_store",
                    orchestrator_name="local_orchestrator",
                ),
            )

            gc = GlobalConfig()
            gc.set_stack_for_repo(repo_path, "local_stack")
            gc.update()

    def get_git_wrapper(self) -> GitWrapper:
        return self.git_wrapper

    def get_service(self) -> LocalService:
        """Returns the active service. For now, always local."""
        return self.service

    def set_active_stack(self, stack_key: Text):
        """Set the active stack for the repo. This change is local for the
        machine.

        Args:
            stack_key: Key of the stack to set active.
        """
        gc = GlobalConfig()
        self.service.get_stack(stack_key)  # check if it exists
        gc.set_stack_for_repo(self.path, stack_key)
        gc.update()

    def get_active_stack_key(self) -> Text:
        """Get the active stack key from global config.

        Returns:
            Currently active stacks key.
        """
        gc = GlobalConfig()
        if self.path not in gc.repo_active_stacks:
            raise AssertionError(f"No active stack set for repo: {self.path}!")
        return gc.repo_active_stacks[self.path]

    def get_active_stack(self) -> BaseStack:
        """Get the active stack from global config.

        Returns:
            Currently active stack.
        """
        return self.service.get_stack(self.get_active_stack_key())

    @track(event=GET_PIPELINES)
    def get_pipelines(self):
        """Gets list of all pipelines."""
        raise NotImplementedError

    def get_pipeline_by_name(self, pipeline_name: Text = None):
        """
        Loads a pipeline just by its name.

        Args:
            pipeline_name (str): Name of pipeline.
        """
        raise NotImplementedError
        # from zenml.pipelines import BasePipeline
        #
        # yamls = self.get_pipeline_file_paths()
        # for y in yamls:
        #     n = BasePipeline.get_name_from_pipeline_name(os.path.basename(y))
        #     if n == pipeline_name:
        #         c = yaml_utils.read_yaml(y)
        #         return BasePipeline.from_config(c)

    def get_pipelines_by_type(self, type_filter: List[Text]) -> List:
        """
        Gets list of pipelines filtered by type.

        Args:
            type_filter (list): list of types to filter by.
        """
        raise NotImplementedError
        # pipelines = self.get_pipelines()
        # return [p for p in pipelines if p.PIPELINE_TYPE in type_filter]

    def get_pipeline_names(self) -> Optional[List[Text]]:
        """Gets list of pipeline (unique) names"""
        raise NotImplementedError
        # from zenml.pipelines import BasePipeline
        #
        # yamls = self.get_pipeline_file_paths(only_file_names=True)
        # return [BasePipeline.get_name_from_pipeline_name(p) for p in yamls]

    @track(event=GET_STEP_VERSION)
    def get_step_by_version(self, step_type: Union[Type, Text], version: Text):
        """
        Gets a Step object by version. There might be many objects of a
        particular Step registered in many pipelines. This function just
        returns the first configuration that it matches.

        Args:
            step_type: either a string specifying full source of the step or a
            python class type.
            version: either sha pin or standard ZenML version pin.
        """
        raise NotImplementedError
        # from zenml.steps.base_step import BaseStep
        # from zenml.utils import source_utils
        #
        # type_str = source_utils.get_module_source_from_class(step_type)
        #
        # for file_path in self.get_pipeline_file_paths():
        #     c = yaml_utils.read_yaml(file_path)
        #     for step_name, step_config in c[keys.GlobalKeys.PIPELINE][
        #         keys.PipelineKeys.STEPS
        #     ].items():
        #         # Get version from source
        #         class_ = source_utils.get_class_source_from_source(
        #             step_config[keys.StepKeys.SOURCE]
        #         )
        #         source_version = source_utils.get_pin_from_source(
        #             step_config[keys.StepKeys.SOURCE]
        #         )
        #
        #         if class_ == type_str and version == source_version:
        #             return BaseStep.from_config(step_config)

    def get_step_versions_by_type(self, step_type: Union[Type, Text]):
        """
        List all registered steps in repository by step_type.

        Args:
            step_type: either a string specifying full source of the step or a
            python class type.
        """
        raise NotImplementedError
        # from zenml.utils import source_utils
        #
        # type_str = source_utils.get_module_source_from_class(step_type)
        #
        # steps_dict = self.get_step_versions()
        # if type_str not in steps_dict:
        #     logger.warning(
        #         f"Type {type_str} not available. Available types: "
        #         f"{list(steps_dict.keys())}"
        #     )
        #     return
        # return steps_dict[type_str]

    @track(event=GET_STEPS_VERSIONS)
    def get_step_versions(self):
        """List all registered steps in repository"""
        raise NotImplementedError
        # from zenml.utils import source_utils
        #
        # steps_dict = {}
        # for file_path in self.get_pipeline_file_paths():
        #     c = yaml_utils.read_yaml(file_path)
        #     for step_name, step_config in c[keys.GlobalKeys.PIPELINE][
        #         keys.PipelineKeys.STEPS
        #     ].items():
        #         # Get version from source
        #         version = source_utils.get_pin_from_source(
        #             step_config[keys.StepKeys.SOURCE]
        #         )
        #         class_ = source_utils.get_class_source_from_source(
        #             step_config[keys.StepKeys.SOURCE]
        #         )
        #
        #         # Add to set of versions
        #         if class_ in steps_dict:
        #             steps_dict[class_].add(version)
        #         else:
        #             steps_dict[class_] = {version}
        # return steps_dict

    def clean(self):
        """Deletes associated metadata store, pipelines dir and artifacts"""
        raise NotImplementedError
