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

import time
from abc import abstractmethod
from typing import Dict, Text, Any, Optional, List
from uuid import uuid4

from zenml.backends.orchestrator import OrchestratorBaseBackend
from zenml.constants import CONFIG_VERSION
from zenml.datasources import BaseDatasource
from zenml.enums import PipelineStatusTypes
from zenml.exceptions import AlreadyExistsException
from zenml.logger import get_logger
from zenml.metadata import ZenMLMetadataStore
from zenml.repo import Repository, ArtifactStore
from zenml.standards import standard_keys as keys
from zenml.steps import BaseStep
from zenml.utils import source_utils
from zenml.utils.analytics_utils import track, CREATE_PIPELINE, RUN_PIPELINE, \
    GET_PIPELINE_ARTIFACTS
from zenml.utils.print_utils import to_pretty_string, PrintStyles

logger = get_logger(__name__)


class BasePipeline:
    """Base class for all ZenML pipelines.

    Every ZenML pipeline should override this class.
    """
    PIPELINE_TYPE = 'base'

    def __init__(self,
                 name: Text = None,
                 enable_cache: Optional[bool] = True,
                 steps_dict: Dict[Text, BaseStep] = None,
                 backend: OrchestratorBaseBackend = None,
                 metadata_store: Optional[ZenMLMetadataStore] = None,
                 artifact_store: Optional[ArtifactStore] = None,
                 datasource: Optional[BaseDatasource] = None,
                 datasource_commit_id: Optional[Text] = None,
                 pipeline_name: Optional[Text] = None,
                 *args, **kwargs):
        """
        Construct a base pipeline. This is a base interface that is meant
        to be overridden in multiple other pipeline use cases.

        Args:
            name: Outward-facing name of the pipeline.
            pipeline_name: A unique name that identifies the pipeline after
             it is run.
            enable_cache: Boolean, indicates whether or not caching
             should be used.
            steps_dict: Optional dict of steps.
            backend: Orchestrator backend.
            metadata_store: Configured metadata store. If None,
             the default metadata store is used.
            artifact_store: Configured artifact store. If None,
             the default artifact store is used.
            datasource: The datasource to use.
            datasource_commit_id: The datasource commit id to use.
        """
        # Generate a name if not given
        if name is None:
            name = str(round(time.time() * 1000))
        self.name = name
        self._immutable = False

        # Metadata store
        if metadata_store:
            self.metadata_store: ZenMLMetadataStore = metadata_store
        else:
            # use default
            self.metadata_store: ZenMLMetadataStore = \
                Repository.get_instance().get_default_metadata_store()

        if pipeline_name:
            # This means its been loaded in through YAML, try to get context
            self.pipeline_name = pipeline_name
            self.file_name = self.pipeline_name + '.yaml'
        else:
            # if pipeline_name is None then its a new pipeline
            self.pipeline_name = self.create_pipeline_name_from_name()
            self.file_name = self.pipeline_name + '.yaml'
            # check duplicates here as its a 'new' pipeline
            self._check_registered()
            track(event=CREATE_PIPELINE)
            logger.info(f'Pipeline {name} created.')

        self.enable_cache = enable_cache

        if steps_dict is None:
            self.steps_dict: Dict[Text, BaseStep] = {}
        else:
            self.steps_dict = steps_dict

        # Default to local
        if backend is None:
            self.backend = OrchestratorBaseBackend()
        else:
            self.backend = backend

        # Artifact store
        if artifact_store:
            self.artifact_store = artifact_store
        else:
            # use default
            self.artifact_store = \
                Repository.get_instance().get_default_artifact_store()

        # Datasource
        if datasource:
            self.datasource = datasource
            self.datasource_commit_id = datasource.get_latest_commit()
        else:
            self.datasource = None
            self.datasource_commit_id = None

        if datasource_commit_id:
            self.datasource_commit_id = datasource_commit_id

        self._source = source_utils.resolve_class(self.__class__)
        self._kwargs = {
            keys.PipelineDetailKeys.NAME: self.pipeline_name,
            keys.PipelineDetailKeys.ENABLE_CACHE: self.enable_cache,
        }
        if kwargs:
            self._kwargs.update(kwargs)

    def __str__(self):
        return to_pretty_string(self.to_config())

    def __repr__(self):
        return to_pretty_string(self.to_config(), style=PrintStyles.PPRINT)

    @property
    def is_executed_in_metadata_store(self):
        try:
            # if we find context, then it has been executed
            self.metadata_store.get_pipeline_context(self)
            return True
        except Exception as _:
            return False

    @abstractmethod
    def get_tfx_component_list(self, config: Dict[Text, Any]) -> List:
        """
        Converts config to TFX components list. This is the point in the
        framework where ZenML Steps get translated into TFX pipelines.

        Args:
            config: dict of ZenML config.
        """
        pass

    @abstractmethod
    def steps_completed(self) -> bool:
        """Returns True if all steps complete, else raises exception"""
        pass

    @staticmethod
    def get_name_from_pipeline_name(pipeline_name: Text):
        """
        Gets name from pipeline name.

        Args:
            pipeline_name (str): simple string name.
        """
        return "_".join(pipeline_name.split('_')[1:-1])

    @classmethod
    def from_config(cls, config: Dict):
        """
        Convert from pipeline config to ZenML Pipeline object.

        All steps are also populated and configuration set to parameters set
        in the config file.

        Args:
            config: a ZenML config in dict-form (probably loaded from YAML).
        """
        # start with artifact store
        artifact_store = ArtifactStore(config[keys.GlobalKeys.ARTIFACT_STORE])

        # metadata store
        metadata_store = ZenMLMetadataStore.from_config(
            config=config[keys.GlobalKeys.METADATA_STORE]
        )

        # orchestration backend
        backend = OrchestratorBaseBackend.from_config(
            config[keys.GlobalKeys.BACKEND])

        # pipeline configuration
        p_config = config[keys.GlobalKeys.PIPELINE]
        kwargs = p_config[keys.PipelineKeys.ARGS]
        pipeline_name = kwargs.pop(keys.PipelineDetailKeys.NAME)
        pipeline_source = p_config[keys.PipelineKeys.SOURCE]

        # populate steps
        steps_dict: Dict = {}
        for step_key, step_config in p_config[keys.PipelineKeys.STEPS].items():
            steps_dict[step_key] = BaseStep.from_config(step_config)

        # datasource
        datasource = BaseDatasource.from_config(
            config[keys.GlobalKeys.PIPELINE])

        # datasource commit
        datasource_commit_id = p_config[keys.PipelineKeys.DATASOURCE_COMMIT_ID]

        class_ = source_utils.load_source_path_class(pipeline_source)

        obj = class_(
            steps_dict=steps_dict,
            backend=backend,
            artifact_store=artifact_store,
            metadata_store=metadata_store,
            datasource=datasource,
            datasource_commit_id=datasource_commit_id,
            pipeline_name=pipeline_name,
            name=cls.get_name_from_pipeline_name(pipeline_name),
            **kwargs
        )
        obj._immutable = True
        return obj

    def _check_registered(self):
        if Repository.get_instance().get_pipeline_by_name(
                self.name) is not None:
            raise AlreadyExistsException(
                name=self.name, resource_type='pipeline')

    def _validate_steps(self):
        """Ensure that steps are of the right type"""
        for step_name, step_val in self.steps_dict.items():
            if not issubclass(type(step_val), BaseStep):
                raise AssertionError(
                    f'Step {step_name} needs to be an object that is a '
                    f'sub-class of: {BaseStep}')

    def add_datasource(self, datasource: BaseDatasource,
                       commit_id: Text = None):
        """
        Add datasource to pipeline.

        Args:
            datasource: class of type BaseDatasource.
            commit_id: optionally the commit of the datasource to use. If
            left None, then latest commit is used.
        """
        self.datasource = datasource
        if commit_id is None:
            self.datasource_commit_id = datasource.get_latest_commit()

    def create_pipeline_name_from_name(self):
        """Creates a unique pipeline name from user-provided name."""
        return self.PIPELINE_TYPE.lower() + '_' + self.name + '_' + str(
            uuid4())

    def get_steps_config(self) -> Dict:
        """Convert Step classes to steps config dict."""
        steps_config = {}
        for step_key, step in self.steps_dict.items():
            steps_config[step_key] = step.to_config()

        return {keys.PipelineKeys.STEPS: steps_config}

    def get_pipeline_config(self):
        """Get pipeline config"""
        steps_config = self.get_steps_config()
        steps_config.update({
            keys.PipelineKeys.ARGS: self._kwargs,
            keys.PipelineKeys.SOURCE: self._source,
            keys.PipelineKeys.DATASOURCE: self.datasource.to_config() if
            self.datasource is not None else {},
            keys.PipelineKeys.DATASOURCE_COMMIT_ID: self.datasource_commit_id,
        })
        return steps_config

    def to_config(self) -> Dict:
        """Converts entire pipeline to ZenML config."""
        return {
            keys.GlobalKeys.VERSION: CONFIG_VERSION,
            keys.GlobalKeys.METADATA_STORE: self.metadata_store.to_config(),
            keys.GlobalKeys.ARTIFACT_STORE: self.artifact_store.path,
            keys.GlobalKeys.BACKEND: self.backend.to_config(),
            keys.GlobalKeys.PIPELINE: self.get_pipeline_config(),
        }

    def get_status(self) -> Text:
        """Get status of pipeline."""
        store = self.metadata_store
        return store.get_pipeline_status(self)

    def register_pipeline(self, config: Dict[Text, Any]):
        """
        Registers a pipeline in the artifact store as a YAML file.

        Args:
            config: dict representation of ZenML config.
        """
        self._check_registered()
        Repository.get_instance().register_pipeline(
            file_name=self.file_name, config=config)

    def load_config(self) -> Dict[Text, Any]:
        """Loads a config dict from yaml file."""
        return Repository.get_instance().load_pipeline_config(
            file_name=self.file_name)

    @track(event=GET_PIPELINE_ARTIFACTS)
    def get_artifacts_uri_by_component(
            self, component_name: Text, resolve_locally: bool = True):
        """
        Gets the artifacts of any component within a pipeline. All artifacts
        are resolved locally if resolve_locally flag is set.

        Args:
            component_name (str): name of component
            resolve_locally (bool): If True, artifact is downloadeded locally.
        """
        status = self.metadata_store.get_pipeline_status(self)
        if status != PipelineStatusTypes.Succeeded.name:
            AssertionError('Cannot retrieve as pipeline is not succeeded.')
        artifacts = self.metadata_store.get_artifacts_by_component(
            self, component_name)
        # Download if not base
        uris = []
        for a in artifacts:
            uris.append(self.artifact_store.resolve_uri_locally(
                a.uri) if resolve_locally else a.uri)
        return uris

    def copy(self, new_name: Text):
        """
        Deep copy the pipeline and therefore remove mutability requirement.

        Args:
            new_name (str): New name for copied pipeline.
        """
        class_ = self.__class__
        args = self.__dict__.copy()

        # Doing this will reset immutability
        args.pop('pipeline_name')
        args['name'] = new_name
        obj = class_(**args)
        obj._immutable = False
        return obj

    def run_config(self, config: Dict[Text, Any]):
        """
        Gets TFX pipeline from config.

        Args:
            config: dict of ZenML config.
        """
        assert issubclass(self.backend.__class__, OrchestratorBaseBackend)
        self.backend.run(config)

    @track(event=RUN_PIPELINE)
    def run(self,
            backend: OrchestratorBaseBackend = None,
            metadata_store: Optional[ZenMLMetadataStore] = None,
            artifact_store: Optional[ArtifactStore] = None):
        """
        Run the pipeline associated with the datasource.

        Args:
            backend: orchestrator backend for pipeline.
            metadata_store: chosen metadata store, if None use default
            artifact_store: chosen artifact store, if None use default
             """

        # TODO: [HIGH] Important, think about separating register and run
        #  and that way ask user to input name while registering pipeline.

        # Resolve default
        if metadata_store:
            logger.warning('Changing the metadata_store or artifact_store '
                           'might cause your pipelines to be '
                           'non-reproducible and non-comparable.')
            self.metadata_store = metadata_store

        if artifact_store:
            logger.warning('Changing the metadata_store or artifact_store '
                           'might cause your pipelines to be '
                           'non-reproducible and non-comparable.')
            self.artifact_store = artifact_store

        if backend:
            self.backend = backend

        # We do not allow ml metadata to get polluted by repeated runs
        if self.is_executed_in_metadata_store:
            logger.info(f'Pipeline: `{self.name}` has already been executed '
                        f'for the connected metadata store. Pipelines are '
                        f'immutable after they run within the same metadata '
                        f'store. If the pipeline failed, then try using '
                        f'the `pipeline.copy(new_name)` method to copy the '
                        f'current `pipeline` and give it a new name.')
            return

        # Check if steps are complete
        self.steps_completed()

        # Validate steps
        self._validate_steps()

        if self._immutable:
            # This means its an 'older' pipeline that has been loaded in via
            # YAML but does not exist in the metadata store, so we are safe
            # to run it without inferring new version pins. This will result
            # in a repeated run.
            logger.info('Pipeline is an immutable state: Any changes made '
                        'after loading it will not be reflected in this run.')
            config = self.load_config()
        else:
            # This means its a brand new pipeline
            config = self.to_config()
            # Register in the repository
            self.register_pipeline(config)

        self.run_config(config)

        # After running, pipeline is immutable
        self._immutable = True
