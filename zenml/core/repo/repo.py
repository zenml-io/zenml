#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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
from pathlib import Path
from typing import Text, List, Dict, Any, Optional, Type

import yaml

from zenml.core.metadata.metadata_wrapper import ZenMLMetadataStore
from zenml.core.repo.artifact_store import ArtifactStore
from zenml.core.repo.git_wrapper import GitWrapper
from zenml.core.repo.global_config import GlobalConfig
from zenml.core.repo.zenml_config import ZenMLConfig
from zenml.utils import path_utils, yaml_utils
from zenml.utils.enums import PipelineStatusTypes
from zenml.utils.zenml_analytics import track, CREATE_REPO, GET_PIPELINES, \
    GET_DATASOURCES, GET_PIPELINE_ARTIFACTS, GET_STEPS, REGISTER_PIPELINE


class Repository:
    """ZenML repository definition. This is a Singleton class.

    Every ZenML project exists inside a ZenML repository.
    """
    __instance__ = None

    def __init__(self, path: Text = None):
        """
        Construct reference a ZenML repository

        Args:
            path (str): Path to root of repository
        """
        if Repository.__instance__ is None:
            if path is None:
                # Start from cwd and traverse up until we find zenml config.
                path = Repository.get_zenml_dir(os.getcwd())

            if not path_utils.is_dir(path):
                raise Exception(f'{path} does not exist or is not a dir!')
            self.path = path

            # Hook up git
            self.git_wrapper = GitWrapper(self.path)

            # Load the ZenML config
            self.zenml_config = ZenMLConfig(self.path)

            Repository.__instance__ = self
        else:
            raise Exception("You cannot create another Repository class!")

    @staticmethod
    def get_zenml_dir(path: Text):
        """
        Recursive function to find the zenml config starting from path.

        Args:
            path (str): starting path
        """
        if ZenMLConfig.is_zenml_dir(path):
            return path

        if path_utils.is_root(path):
            raise Exception(
                'Looks like you used ZenML outside of a ZenML repo. '
                'Please init a ZenML repo first before you using '
                'the framework.')
        return Repository.get_zenml_dir(Path(path).parent)

    @staticmethod
    def get_instance():
        """ Static method to fetch the current instance."""
        if not Repository.__instance__:
            Repository()
        return Repository.__instance__

    @staticmethod
    @track(event=CREATE_REPO)
    def init_repo(repo_path: Text, artifact_store_path: Text = None,
                  metadata_store: Optional[Type[ZenMLMetadataStore]] = None,
                  pipelines_dir: Text = None,
                  analytics_opt_in: bool = None):
        """
        Initializes a git repo with zenml.

        Args:
            repo_path (str): path to root of a git repo
            metadata_store: metadata store definition
            artifact_store_path (str): path where to store artifacts
            pipelines_dir (str): path where to store pipeline configs.
            analytics_opt_in (str): opt-in flag for analytics code.

        Raises:
            InvalidGitRepositoryError: If repository is not a git repository.
            NoSuchPathError: If the repo_path does not exist.
        """
        # check whether its a git repo by initializing GitWrapper
        GitWrapper(repo_path)

        # use the underlying ZenMLConfig class to create the config
        ZenMLConfig.create_config(
            repo_path, artifact_store_path, metadata_store, pipelines_dir)

        # create global config
        global_config = GlobalConfig.get_instance()
        if analytics_opt_in is not None:
            global_config.set_analytics_opt_in(analytics_opt_in)

    def get_artifact_store(self) -> ArtifactStore:
        return self.zenml_config.get_artifact_store()

    def get_metadata_store(self):
        return self.zenml_config.get_metadata_store()

    def get_git_wrapper(self) -> GitWrapper:
        return self.git_wrapper

    @track(event=GET_STEPS)
    def get_steps(self):
        """List all registered steps in repository"""
        pass

    @track(event=GET_PIPELINES)
    def get_pipelines(self, type_filter: List[Text] = None):
        """
        Gets list of pipelines, optionally filtered by type.

        Args:
            type_filter (list): list of types to filter by.
        """
        from zenml.core.pipelines.pipeline_factory import pipeline_factory
        pipelines = []
        for file_path in self.get_pipeline_file_paths():
            file_name = Path(file_path).name
            pipeline_type = pipeline_factory.get_type_from_file_name(file_name)
            pipeline_class = pipeline_factory.get_single_type(pipeline_type)
            with open(file_path, 'r') as f:
                c = yaml.load(f)
                pipelines.append(pipeline_class.from_config(c))

        if type_filter:
            # filter by type
            return [p for p in pipelines if p.pipeline_type in type_filter]
        else:
            # return all
            return pipelines

    def get_pipeline_names(self) -> Optional[List[Text]]:
        """Gets list of pipeline (unique) names"""
        store = self.zenml_config.get_metadata_store()

        contexts = store.get_pipeline_contexts()
        return [c.name for c in contexts]

    def get_pipeline_file_paths(self, only_file_names: bool = False) -> \
            Optional[List[Text]]:
        """Gets list of pipeline file path"""
        pipelines_dir = self.zenml_config.get_pipelines_dir()

        if not path_utils.is_dir(pipelines_dir):
            return []
        return path_utils.list_dir(pipelines_dir, only_file_names)

    @track(event=GET_DATASOURCES)
    def get_datasources(self) -> List:
        """
        Get all datasources in this repo.

        Returns: list of datasources used in this repo
        """
        pass

    def get_hyperparameters(self):
        """
        Hyper-parameter list of all pipelines in repo
        """
        pass

    @track(event=GET_PIPELINE_ARTIFACTS)
    def get_artifacts_uri_by_component(self, pipeline_name: Text,
                                       component_name: Text):
        """
        Gets the artifacts of any component within a pipeline. All artifacts
        are resolved locally, even if artifact store is remote.

        Args:
            pipeline_name (str): name of pipeline
            component_name (str): name of component
        """
        # mlmd
        metadata_store = self.get_metadata_store()
        status = metadata_store.get_pipeline_status(pipeline_name)
        if status != PipelineStatusTypes.Succeeded.name:
            AssertionError('Cannot retrieve as pipeline is not succeeded.')
        # if component_name not in GDPCOmponents:
        #     raise AssertionError('Component must be one of {}')
        artifacts = metadata_store.get_artifacts_by_component(pipeline_name,
                                                              component_name)

        # Download if not local
        uris = []
        for a in artifacts:
            artifact_store = self.get_artifact_store()
            uris.append(artifact_store.resolve_uri_locally(a.uri))

        return uris

    def get_hyperparameters_pipeline(self):
        pass

    @track(event=REGISTER_PIPELINE)
    def register_pipeline(self, file_name: Text, config: Dict[Text, Any]):
        """
        Registers a pipeline in the artifact store as a YAML file.

        Args:
            file_name (dict): file name of pipeline
            config (dict): dict representation of ZenML config
        """
        pipelines_dir = self.zenml_config.get_pipelines_dir()

        # Create dir
        path_utils.create_dir_if_not_exists(pipelines_dir)

        # Write
        yaml_utils.write_yaml(os.path.join(pipelines_dir, file_name), config)

    def compare_pipelines(self):
        pass
