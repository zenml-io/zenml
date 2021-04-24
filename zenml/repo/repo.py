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
from typing import Text, List, Dict, Any, Optional, Union, Type

from zenml.exceptions import InitializationException
from zenml.logger import get_logger
from zenml.metadata import ZenMLMetadataStore
from zenml.repo import ArtifactStore, GitWrapper, GlobalConfig, ZenMLConfig
from zenml.repo.constants import ZENML_DIR_NAME
from zenml.standards import standard_keys as keys
from zenml.utils import path_utils, yaml_utils
from zenml.utils.analytics_utils import track, CREATE_REPO, GET_PIPELINES, \
    GET_DATASOURCES, GET_STEPS_VERSIONS, \
    REGISTER_PIPELINE, GET_STEP_VERSION

logger = get_logger(__name__)


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
                try:
                    # Start from cwd and traverse up until find zenml config.
                    path = Repository.get_zenml_dir(os.getcwd())
                except Exception:
                    # If there isnt a zenml.config, use the cwd
                    path = os.getcwd()

            if not path_utils.is_dir(path):
                raise Exception(f'{path} does not exist or is not a dir!')
            self.path = path

            # Hook up git, path needs to have a git folder.
            self.git_wrapper = GitWrapper(self.path)

            # Load the ZenML config
            try:
                self.zenml_config = ZenMLConfig(self.path)
            except InitializationException:
                # We allow this because we of the GCP orchestrator for now
                self.zenml_config = None

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
        return Repository.get_zenml_dir(str(Path(path).parent))

    @staticmethod
    def get_instance(path: Text = None):
        """ Static method to fetch the current instance."""
        logger.debug('Repository instance fetched.')
        if not Repository.__instance__:
            Repository(path)
        return Repository.__instance__

    @staticmethod
    @track(event=CREATE_REPO)
    def init_repo(repo_path: Text, artifact_store_path: Text = None,
                  metadata_store: Optional[ZenMLMetadataStore] = None,
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
        git_wrapper = GitWrapper(repo_path)
        # Do proper checks and add to .gitignore
        git_wrapper.add_gitignore([ZENML_DIR_NAME + '/'])

        # use the underlying ZenMLConfig class to create the config
        ZenMLConfig.to_config(
            repo_path, artifact_store_path, metadata_store, pipelines_dir)

        # create global config
        global_config = GlobalConfig.get_instance()
        if analytics_opt_in is not None:
            global_config.set_analytics_opt_in(analytics_opt_in)

    def get_default_artifact_store(self) -> Optional[ArtifactStore]:
        self._check_if_initialized()
        return self.zenml_config.get_artifact_store()

    def get_default_metadata_store(self):
        self._check_if_initialized()
        return self.zenml_config.get_metadata_store()

    def get_default_pipelines_dir(self) -> Text:
        self._check_if_initialized()
        return self.zenml_config.get_pipelines_dir()

    def get_git_wrapper(self) -> GitWrapper:
        self._check_if_initialized()
        return self.git_wrapper

    # TODO [MEDIUM]: Potentially move these three to relevant Base classes.
    def get_artifact_store_from_file_path(self, file_path: Text):
        """
        Gets artifact store from a pipeline config file path.
        Args:
            file_path (Text): Path to pipeline YAML file.
        """
        config = yaml_utils.read_yaml(file_path)
        return ArtifactStore(config[keys.GlobalKeys.ARTIFACT_STORE])

    def get_metadata_store_from_file_path(self, file_path: Text):
        """
        Gets metadata store from a pipeline config file path.
        Args:
            file_path (Text): Path to pipeline YAML file.
        """
        config = yaml_utils.read_yaml(file_path)
        return ZenMLMetadataStore.from_config(
            config[keys.GlobalKeys.METADATA_STORE])

    def get_orchestrator_backend_from_file_path(self, file_path: Text):
        """
        Gets orchestrator backend from a pipeline config file path.
        Args:
            file_path (Text): Path to pipeline YAML file.
        """
        from zenml.backends.orchestrator.base.orchestrator_base_backend \
            import OrchestratorBaseBackend
        config = yaml_utils.read_yaml(file_path)
        return OrchestratorBaseBackend.from_config(
            config[keys.GlobalKeys.BACKEND])

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
        from zenml.utils import source_utils
        from zenml.steps.base_step import BaseStep

        type_str = source_utils.get_module_source_from_class(step_type)

        for file_path in self.get_pipeline_file_paths():
            c = yaml_utils.read_yaml(file_path)
            for step_name, step_config in c[keys.GlobalKeys.PIPELINE][
                keys.PipelineKeys.STEPS].items():
                # Get version from source
                class_ = source_utils.get_class_source_from_source(
                    step_config[keys.StepKeys.SOURCE])
                source_version = source_utils.get_pin_from_source(
                    step_config[keys.StepKeys.SOURCE])

                if class_ == type_str and version == source_version:
                    return BaseStep.from_config(step_config)

    def get_step_versions_by_type(self, step_type: Union[Type, Text]):
        """
        List all registered steps in repository by step_type.

        Args:
            step_type: either a string specifying full source of the step or a
            python class type.
        """
        from zenml.utils import source_utils
        type_str = source_utils.get_module_source_from_class(step_type)

        steps_dict = self.get_step_versions()
        if type_str not in steps_dict:
            logger.warning(f'Type {type_str} not available. Available types: '
                           f'{list(steps_dict.keys())}')
            return
        return steps_dict[type_str]

    @track(event=GET_STEPS_VERSIONS)
    def get_step_versions(self):
        """List all registered steps in repository"""
        from zenml.utils import source_utils
        steps_dict = {}
        for file_path in self.get_pipeline_file_paths():
            c = yaml_utils.read_yaml(file_path)
            for step_name, step_config in c[keys.GlobalKeys.PIPELINE][
                keys.PipelineKeys.STEPS].items():
                # Get version from source
                version = source_utils.get_pin_from_source(
                    step_config[keys.StepKeys.SOURCE])
                class_ = source_utils.get_class_source_from_source(
                    step_config[keys.StepKeys.SOURCE])

                # Add to set of versions
                if class_ in steps_dict:
                    steps_dict[class_].add(version)
                else:
                    steps_dict[class_] = {version}
        return steps_dict

    def get_datasource_by_name(self, name: Text):
        """
        Get all datasources in this repo.

        Returns: list of datasources used in this repo
        """
        all_datasources = self.get_datasources()
        for d in all_datasources:
            if name == d.name:
                return d

    def get_datasource_id_by_name(self, name: Text) -> List:
        """
        Get ID of a datasource by just its name.

        Returns: ID of datasource.
        """
        for file_path in self.get_pipeline_file_paths():
            c = yaml_utils.read_yaml(file_path)
            src = c[keys.GlobalKeys.PIPELINE][keys.PipelineKeys.DATASOURCE]
            if keys.DatasourceKeys.NAME in src:
                if name == src[keys.DatasourceKeys.NAME]:
                    return src[keys.DatasourceKeys.ID]

    def get_datasource_names(self) -> List:
        """
        Get all datasources in this repo.

        Returns: List of datasource names used in this repo.
        """
        n = []
        for file_path in self.get_pipeline_file_paths():
            c = yaml_utils.read_yaml(file_path)
            src = c[keys.GlobalKeys.PIPELINE][keys.PipelineKeys.DATASOURCE]
            if keys.DatasourceKeys.NAME in src:
                n.append(src[keys.DatasourceKeys.NAME])
        return list(set(n))

    @track(event=GET_DATASOURCES)
    def get_datasources(self) -> List:
        """
        Get all datasources in this repo.

        Returns: list of datasources used in this repo
        """
        from zenml.datasources import BaseDatasource

        datasources = []
        datasources_name = set()
        for file_path in self.get_pipeline_file_paths():
            c = yaml_utils.read_yaml(file_path)
            ds = BaseDatasource.from_config(c[keys.GlobalKeys.PIPELINE])
            if ds and ds.name not in datasources_name:
                datasources.append(ds)
                datasources_name.add(ds.name)
        return datasources

    def get_pipeline_by_name(self, pipeline_name: Text = None):
        """
        Loads a pipeline just by its name.

        Args:
            pipeline_name (str): Name of pipeline.
        """
        from zenml.pipelines import BasePipeline
        yamls = self.get_pipeline_file_paths()
        for y in yamls:
            n = BasePipeline.get_name_from_pipeline_name(os.path.basename(y))
            if n == pipeline_name:
                c = yaml_utils.read_yaml(y)
                return BasePipeline.from_config(c)

    def get_pipelines_by_type(self, type_filter: List[Text]) -> List:
        """
        Gets list of pipelines filtered by type.

        Args:
            type_filter (list): list of types to filter by.
        """
        pipelines = self.get_pipelines()
        return [p for p in pipelines if p.PIPELINE_TYPE in type_filter]

    def get_pipeline_names(self) -> Optional[List[Text]]:
        """Gets list of pipeline (unique) names"""
        from zenml.pipelines import BasePipeline
        yamls = self.get_pipeline_file_paths(only_file_names=True)
        return [BasePipeline.get_name_from_pipeline_name(p) for p in yamls]

    def get_pipeline_file_paths(self, only_file_names: bool = False) -> \
            Optional[List[Text]]:
        """Gets list of pipeline file path"""
        self._check_if_initialized()

        pipelines_dir = self.zenml_config.get_pipelines_dir()

        if not path_utils.is_dir(pipelines_dir):
            return []
        all_files = path_utils.list_dir(pipelines_dir, only_file_names)
        return [x for x in all_files if yaml_utils.is_yaml(x)]

    def get_pipelines_by_datasource(self, datasource):
        """
        Gets list of pipelines associated with datasource.

        Args:
            datasource (BaseDatasource): object of type BaseDatasource.
        """
        from zenml.pipelines import BasePipeline
        pipelines = []
        for file_path in self.get_pipeline_file_paths():
            c = yaml_utils.read_yaml(file_path)
            if keys.DatasourceKeys.ID in c[keys.GlobalKeys.PIPELINE][
                keys.PipelineKeys.DATASOURCE]:
                if c[keys.GlobalKeys.PIPELINE][keys.PipelineKeys.DATASOURCE][
                    keys.DatasourceKeys.ID] == datasource._id:
                    pipelines.append(BasePipeline.from_config(c))
        return pipelines

    def get_pipeline_f_paths_by_datasource_id(self, datasource_id: Text):
        """
        Gets list of file path associated with a datasource id.

        Args:
            datasource_id (Text): id of datasource.
        """
        paths = []
        for file_path in self.get_pipeline_file_paths():
            c = yaml_utils.read_yaml(file_path)
            if keys.DatasourceKeys.ID in c[keys.GlobalKeys.PIPELINE][
                keys.PipelineKeys.DATASOURCE]:
                if c[keys.GlobalKeys.PIPELINE][keys.PipelineKeys.DATASOURCE][
                    keys.DatasourceKeys.ID] == datasource_id:
                    paths.append(file_path)
        return paths

    @track(event=GET_PIPELINES)
    def get_pipelines(self) -> List:
        """Gets list of all pipelines."""
        from zenml.pipelines import BasePipeline
        pipelines = []
        for file_path in self.get_pipeline_file_paths():
            c = yaml_utils.read_yaml(file_path)
            pipelines.append(BasePipeline.from_config(c))
        return pipelines

    @track(event=REGISTER_PIPELINE)
    def register_pipeline(self, file_name: Text, config: Dict[Text, Any]):
        """
        Registers a pipeline in the artifact store as a YAML file.

        Args:
            file_name (str): file name of pipeline
            config (dict): dict representation of ZenML config
        """
        self._check_if_initialized()

        pipelines_dir = self.zenml_config.get_pipelines_dir()

        # Create dir
        path_utils.create_dir_if_not_exists(pipelines_dir)

        # Write
        yaml_utils.write_yaml(os.path.join(pipelines_dir, file_name), config)

    def load_pipeline_config(self, file_name: Text) -> Dict[Text, Any]:
        """
        Loads a ZenML config from YAML.

        Args:
            file_name (str): file name of pipeline
        """
        self._check_if_initialized()
        pipelines_dir = self.zenml_config.get_pipelines_dir()
        return yaml_utils.read_yaml(os.path.join(pipelines_dir, file_name))

    def compare_training_runs(self, port: int = 0, datasource=None):
        """Launch the compare app for all training pipelines in repo"""
        from zenml.utils.post_training.post_training_utils import \
            launch_compare_tool
        launch_compare_tool(port, datasource)

    def clean(self):
        """Deletes associated metadata store, pipelines dir and artifacts"""
        raise NotImplementedError

    def _check_if_initialized(self):
        if self.zenml_config is None:
            raise InitializationException
