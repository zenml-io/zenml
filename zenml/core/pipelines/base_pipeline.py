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
"""Base High-level ZenML Pipeline definition"""

import logging
from abc import abstractmethod
from typing import Dict, Text, Any, Optional, List, Type
from uuid import uuid4

from tfx.orchestration import pipeline

from zenml.core.backends.base_backend import BaseBackend
from zenml.core.backends.orchestrator.orchestrator_local_backend import \
    OrchestratorLocalBackend
from zenml.core.metadata.metadata_wrapper import ZenMLMetadataStore
from zenml.core.repo.artifact_store import ArtifactStore
from zenml.core.repo.repo import Repository
from zenml.core.repo.zenml_config import METADATA_KEY, ARTIFACT_STORE_KEY
from zenml.core.steps.base_step import BaseStep
from zenml.utils.zenml_analytics import track, CREATE_PIPELINE, RUN_PIPELINE


class BasePipeline:
    """Base class for all ZenML pipelines.

    Every ZenML pipeline should override this class.
    """
    PIPELINE_TYPE = 'base'

    @track(event=CREATE_PIPELINE)
    def __init__(self,
                 name: Text,
                 pipeline_name: Optional[Text] = None,
                 enable_cache: Optional[bool] = True,
                 steps_dict: Dict[Text, BaseStep] = None,
                 backends_dict: Dict[Text, BaseBackend] = None,
                 metadata_store: Optional[ZenMLMetadataStore] = None,
                 artifact_store: Optional[ArtifactStore] = None,
                 *args, **kwargs):
        """
        Construct a base pipeline.

        Args:
            name: outwards-facing name of the pipeline
            pipeline_name: unique name that identifies the pipeline after
            its run
            enable_cache: boolean indicator whether caching should be used
            steps_dict: optional dict of steps
            backends_dict: optional dict of backends
            metadata_store: chosen metadata store, if None use default
            artifact_store: chosen artifact store, if None use default
        """
        self.repo: Repository = Repository.get_instance()
        self.name = name
        if pipeline_name:
            self.pipeline_name = pipeline_name
        else:
            self.pipeline_name = BasePipeline.create_pipeline_name_from_name(
                self.name)

        # TODO: [MED] Evaluate whether a factory pattern makes sense for this
        from zenml.core.pipelines.pipeline_factory import pipeline_factory
        self.pipeline_type = pipeline_factory.get_type_from_pipeline(
            self.__class__)
        self.file_name = pipeline_factory.create_file_name(self)

        self.enable_cache = enable_cache

        if steps_dict is None:
            self.steps_dict: Dict[Text, Type[BaseStep]] = {}
        else:
            self.steps_dict = steps_dict

        # Backends
        if backends_dict is None:
            self.backends_dict: Dict[Text, BaseBackend] = \
                self.get_default_backends()
        else:
            self.backends_dict = backends_dict

        # Metadata store
        if metadata_store:
            self.metadata_store = metadata_store
        else:
            # use default
            self.metadata_store = self.repo.get_metadata_store()

        # Artifact store
        if artifact_store:
            self.metadata_store = metadata_store
        else:
            # use default
            self.artifact_store = self.repo.get_artifact_store()

        # check duplicates
        if self.file_name in self.repo.get_pipeline_file_paths(
                only_file_names=True):
            raise AssertionError(f'Pipeline names must be unique in the '
                                 f'repository. There is already a pipeline '
                                 f'called {self.name}')

    @staticmethod
    def create_pipeline_name_from_name(name: Text):
        """
        Creates a unique pipeline name from user-provided name.

        Args:
            name (str): simple string name.
        """
        return name + '_' + str(uuid4())

    @staticmethod
    def get_name_from_pipeline_name(pipeline_name: Text):
        """
        Gets name from pipeline name.

        Args:
            pipeline_name (str): simple string name.
        """
        return pipeline_name.split('_')[1]

    @classmethod
    def from_config(cls, config: Dict):
        """
        Convert from pipeline config to ZenML Pipeline object.

        All steps are also populated and configuration set to parameters set
        in the config file.

        Args:
            config: a ZenML config in dict-form (probably loaded from YAML).
        """
        # populate steps
        steps_dict: Dict = {}
        for step_key, step_config in config['steps'].items():
            steps_dict[step_key] = BaseStep.from_config(step_config)

        env = config['environment']
        pipeline_name = env['pipeline_name']
        name = BasePipeline.get_name_from_pipeline_name(
            pipeline_name=pipeline_name)

        backends_dict: Dict = {}
        for backend_key, backend_config in env['backends'].items():
            backends_dict[backend_key] = BaseBackend.from_config(
                backend_config)

        artifact_store = ArtifactStore(env[ARTIFACT_STORE_KEY])
        metadata_store = ZenMLMetadataStore.from_config(
            config=env[METADATA_KEY]
        )

        return cls(name=name, pipeline_name=pipeline_name,
                   enable_cache=env['enable_cache'], steps_dict=steps_dict,
                   backends_dict=backends_dict, artifact_store=artifact_store,
                   metadata_store=metadata_store)

    def get_steps_config(self) -> Dict:
        """Convert Step classes to steps config dict."""
        steps_config = {}
        for step_key, step in self.steps_dict.items():
            steps_config[step_key] = step.to_config()

        # TODO: [HIGH] Hook up to constant when @bcdurak is done with parsing
        return {'steps': steps_config}

    def get_spec(self) -> Dict:
        """Get spec as a dict."""
        backends_config_dict = {}
        for b in self.backends_dict.values():
            backends_config_dict.update(b.to_config())

        return {
            'pipeline_name': self.pipeline_name,
            'enable_cache': self.enable_cache,
            'backends': backends_config_dict,
            'artifact_store': self.artifact_store.path,
            'metadata': self.metadata_store.to_config()
        }

    def to_config(self) -> Dict:
        """Converts pipeline to ZenML config."""
        # Create a ZenML pipeline.config.yaml
        steps_config = self.get_steps_config()

        # Add env config to it
        spec = self.get_spec()

        steps_config.update({
            'environment': spec,
            'version': '0.0.1',  # TODO: [HIGH] Replace with constant version.
        })
        return steps_config

    def get_status(self) -> Text:
        """Get status of pipeline."""
        store = self.repo.get_metadata_store()
        return store.get_pipeline_status(self.name)

    @abstractmethod
    def get_tfx_pipeline(self, config: Dict[Text, Any]) -> pipeline.Pipeline:
        """
        Converts spec to TFX pipeline. This is the point in the framework where
        Steps (which are basically configs now) get translated into TFX
        pipelines to be run.

        Args:
            config: dict of ZenML config.
        """
        pass

    def register_pipeline(self, config: Dict[Text, Any]):
        """
        Registers a pipeline in the artifact store as a YAML file.

        Args:
            config: dict representation of ZenML config.
        """
        self.repo.register_pipeline(file_name=self.file_name, config=config)

    def get_default_backends(self) -> Dict:
        """Gets list of default backends for this pipeline."""
        # For base class, orchestration is always necessary
        return {
            OrchestratorLocalBackend.BACKEND_KEY: OrchestratorLocalBackend()
        }

    def run_tfx_pipeline(self, tfx_pipeline: pipeline.Pipeline):
        """
        Runs the passed tfx_pipeline.

        Args:
            tfx_pipeline:
        """
        from tfx.orchestration.local.local_dag_runner import LocalDagRunner
        LocalDagRunner().run(tfx_pipeline)

    @abstractmethod
    def is_completed(self) -> bool:
        """Returns True if all steps complete, else raises exception"""
        pass

    @track(event=RUN_PIPELINE)
    def run(self,
            backends: Optional[List[Type[BaseBackend]]] = None,
            metadata_store: Optional[ZenMLMetadataStore] = None,
            artifact_store: Optional[ArtifactStore] = None):
        """
        Run the pipeline associated with the datasource.

        Args:
            backends (list): list of backends to use for this
            metadata_store: chosen metadata store, if None use default
            artifact_store: chosen artifact store, if None use default
             """

        # TODO: [HIGH] Important, think about seperating register and run
        #  and that way ask user to input name while registering pipeline.

        # Resolve default
        if metadata_store:
            logging.warning('Changing the metadata_store or artifact_store '
                            'might cause your pipelines to be '
                            'non-reproducible and non-comparable.')
            self.metadata_store = metadata_store

        if artifact_store:
            logging.warning('Changing the metadata_store or artifact_store '
                            'might cause your pipelines to be '
                            'non-reproducible and non-comparable.')
            self.metadata_store = metadata_store

        # Check if steps are complete
        self.is_completed()

        # Resolve backends compatibility
        for b in backends:
            if b.BACKEND_KEY not in self.backends_dict:
                raise Exception(f'Backend {b} not supported!')
            self.backends_dict[b.BACKEND_KEY] = b

        # Get the config dict
        config = self.to_config()

        # Register in the repository
        self.register_pipeline(config)

        # Convert it to TFX pipeline
        tfx_pipeline = self.get_tfx_pipeline(config)

        # Run the pipeline
        self.run_tfx_pipeline(tfx_pipeline)
