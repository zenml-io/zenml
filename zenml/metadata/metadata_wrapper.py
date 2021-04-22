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


from abc import abstractmethod
from typing import Text, Dict

from ml_metadata.metadata_store import metadata_store

from zenml.standards.standard_keys import MLMetadataKeys
from zenml.enums import MLMetadataTypes
from zenml.enums import PipelineStatusTypes
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.utils.print_utils import to_pretty_string, PrintStyles

logger = get_logger(__name__)


class ZenMLMetadataStore:
    STORE_TYPE = None
    RUN_TYPE_PROPERTY_NAME = 'run'

    def __str__(self):
        return to_pretty_string(self.to_config())

    def __repr__(self):
        return to_pretty_string(self.to_config(), style=PrintStyles.PPRINT)

    @property
    def store(self):
        return metadata_store.MetadataStore(self.get_tfx_metadata_config())

    @classmethod
    def from_config(cls, config: Dict):
        """
        Converts ZenML config to ZenML Metadata Store.

        Args:
            config (dict): ZenML config block for metadata.
        """
        from zenml.metadata.metadata_wrapper_factory import \
            wrapper_factory
        store_type = config[MLMetadataKeys.TYPE]
        store_types = list(MLMetadataTypes.__members__.keys())
        if store_type not in store_types:
            raise AssertionError(f'store_type must be one of: {store_types}')
        args = config[MLMetadataKeys.ARGS]
        class_ = wrapper_factory.get_single_metadata_wrapper(store_type)

        try:
            obj = class_(**args)
        except TypeError as e:
            logger.error(str(e))
            import inspect
            args = inspect.getfullargspec(class_).args
            args.remove('self')
            raise Exception(f'args must include only: {args}')
        return obj

    @abstractmethod
    def get_tfx_metadata_config(self):
        pass

    def to_config(self) -> Dict:
        """
        Converts from ZenML Metadata store back to config.
        """
        store_types = list(MLMetadataTypes.__members__.keys())
        if self.STORE_TYPE not in store_types:
            raise AssertionError(f'store_type must be one of: {store_types}')

        args_dict = self.__dict__.copy()
        return {
            MLMetadataKeys.TYPE: self.STORE_TYPE,
            MLMetadataKeys.ARGS: args_dict
        }

    def get_pipeline_status(self, pipeline) -> Text:
        """
        Query metadata store to find status of pipeline.

        Args:
            pipeline (BasePipeline): a ZenML pipeline object
        """
        try:
            components_status = self.get_components_status(pipeline)
        except:
            return PipelineStatusTypes.NotStarted.name

        for status in components_status.values():
            if status != 'complete' and status != 'cached':
                return PipelineStatusTypes.Running.name
        return PipelineStatusTypes.Succeeded.name

    def get_pipeline_executions(self, pipeline):
        """
        Get executions of pipeline.

        Args:
            pipeline (BasePipeline): a ZenML pipeline object
        """
        c = self.get_pipeline_context(pipeline)
        return self.store.get_executions_by_context(c.id)

    def get_components_status(self, pipeline):
        """
        Returns status of components in pipeline.

        Args:
            pipeline (BasePipeline): a ZenML pipeline object

        Returns: dict of type { component_name : component_status }
        """
        pipeline_executions = self.get_pipeline_executions(pipeline)
        return {
            e.properties['component_id'].string_value: e.properties[
                'state'].string_value for e in
            pipeline_executions
        }

    def get_artifacts_by_component(self, pipeline, component_name: Text):
        """
        Args:
            pipeline (BasePipeline): a ZenML pipeline object
            component_name:
        """
        # First , you get the execution associated with the component
        e = self.get_component_execution(pipeline, component_name)

        if e is None:
            raise DoesNotExistException(
                name=component_name,
                reason=f'The pipeline {pipeline.name} does not have the '
                       f'associated {component_name} Step.')

        # Second, you will get artifacts
        return self.get_artifacts_by_execution(e.id)

    def get_component_execution(self, pipeline, component_name: Text):
        pipeline_executions = self.get_pipeline_executions(pipeline)
        for e in pipeline_executions:
            # TODO: [LOW] Create a more refined way to find components.
            if component_name == e.properties['component_id'].string_value:
                return e

    def get_pipeline_context(self, pipeline):
        # We rebuild context for ml metadata here.
        prefix = pipeline.artifact_store.unique_id
        run_id = f'{prefix}.{pipeline.pipeline_name}'
        logger.debug(f'Looking for run_id {run_id} in metadata store: '
                     f'{self.to_config()}')
        run_context = self.store.get_context_by_type_and_name(
            type_name=self.RUN_TYPE_PROPERTY_NAME,
            context_name=run_id
        )
        if run_context is None:
            raise DoesNotExistException(
                name=pipeline.pipeline_name,
                reason=f'The pipeline does not exist in metadata store '
                       f'because it has not been run yet. Please run the '
                       f'pipeline before trying to fetch artifacts.')
        return run_context

    def get_artifacts_by_execution(self, execution_id):
        # First get all the events for this execution
        """
        Args:
            execution_id:
        """
        events = self.store.get_events_by_execution_ids([execution_id])

        artifact_ids = []
        for e in events:
            # MAJOR Assumptions: 4 means its output channel
            if e.type == 4:
                artifact_ids.append(e.artifact_id)
                break

        if not artifact_ids:
            raise AssertionError("This execution has no output artifact.")

        # Get artifacts
        return self.store.get_artifacts_by_id(artifact_ids)
