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

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.config.global_config import GlobalConfig
from zenml.core.git_wrapper import GitWrapper
from zenml.core.local_service import LocalService
from zenml.exceptions import InitializationException
from zenml.logger import get_logger
from zenml.metadata.base_metadata_store import BaseMetadataStore
from zenml.pipelines.base_pipeline import BasePipeline
from zenml.providers.base_provider import BaseProvider
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
        self.pm = LocalService()

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
        provider: BaseProvider = BaseProvider(),
        analytics_opt_in: bool = None,
    ):
        """
        Initializes a git repo with zenml.

        Args:
            repo_path (str): path to root of a git repo
            provider: Initial provider.
            analytics_opt_in: opt-in flag for analytics code.

        Raises:
            InvalidGitRepositoryError: If repository is not a git repository.
            NoSuchPathError: If the repo_path does not exist.
        """
        # edit global config
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

    def get_git_wrapper(self) -> GitWrapper:
        return self.git_wrapper

    def get_providers(self) -> List[BaseProvider]:
        """Returns a list of all registered providers."""
        return self.pm.get_providers()

    def get_metadata_stores(self) -> List[BaseMetadataStore]:
        """Returns a list of all registered metadata stores."""
        return [BaseMetadataStore()]

    def get_artifact_stores(self) -> List[BaseArtifactStore]:
        """Returns a list of all registered artifact stores."""

    def get_orchestrators(self) -> List[Text]:
        """Returns a list of all registered orchestrators."""
        return ["Local"]

    @track(event=GET_PIPELINES)
    def get_pipelines(self) -> List[BasePipeline]:
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

    def register_provider(self, provider: BaseProvider):
        """Registers a provider.

        Args:
            provider: A provider to register.
        """
        raise NotImplementedError

    def register_artifact_store(self, artifact_store: BaseArtifactStore):
        """Registers an artifact store.

        Args:
            artifact_store: An artifact_store to register.
        """
        raise NotImplementedError

    def register_metadata_store(self, metadata_store: BaseMetadataStore):
        """Registers a metadata store.

        Args:
            metadata_store: A metadata_store to register.
        """
        raise NotImplementedError

    def register_orchestrator(self, orchestrator: Text):
        """Registers a orchestrator.

        Args:
            orchestrator: A orchestrator to register.
        """
        raise NotImplementedError

    def clean(self):
        """Deletes associated metadata store, pipelines dir and artifacts"""
        raise NotImplementedError
