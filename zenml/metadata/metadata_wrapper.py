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

from zenml.enums import MLMetadataTypes
from zenml.enums import PipelineStatusTypes
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.standards.standard_keys import MLMetadataKeys
from zenml.utils.print_utils import to_pretty_string, PrintStyles

logger = get_logger(__name__)

STATE_MAPPING = {0: 'unknown',
                 1: 'new',
                 2: 'running',
                 3: 'complete',
                 4: 'failed',
                 5: 'cached',
                 6: 'cancelled'}


class ZenMLMetadataStore:
    STORE_TYPE = None
    RUN_TYPE_NAME = 'pipeline_run'
    NODE_TYPE_NAME = 'node'

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

    def get_data_pipeline_names_from_datasource_name(self,
                                                     datasource_name: Text):
        """
        Gets all data pipeline names from the datasource name.

        Args:
            datasource_name: name of datasource.
        """
        from zenml.pipelines.data_pipeline import DataPipeline

        run_contexts = self.store.get_contexts_by_type(
            self.RUN_TYPE_NAME)

        # TODO [LOW]:
        #  get the data pipelines only by doing an ugly hack. These data
        #  pipelines will always start with `data_`. This needs to change soon
        run_contexts = [x for x in run_contexts if
                        x.name.startswith(DataPipeline.PIPELINE_TYPE)]

        # now filter to the datasource name through executions
        pipelines_names = []
        for c in run_contexts:
            es = self.store.get_executions_by_context(c.id)
            for e in es:
                if 'name' in e.custom_properties and e.custom_properties[
                    'name'].string_value == datasource_name:
                    pipelines_names.append(c.name)
        return pipelines_names

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
        result = {}
        pipeline_executions = self.get_pipeline_executions(pipeline)
        for e in pipeline_executions:
            contexts = self.store.get_contexts_by_execution(e.id)
            node_contexts = [c for c in contexts if c.type_id == 3]
            if node_contexts:
                component_name = node_contexts[0].name.split('.')[-1]
                result[component_name] = STATE_MAPPING[e.last_known_state]

        return result

    def get_artifacts_by_component(self, pipeline, component_name: Text):
        """
        Args:
            pipeline (BasePipeline): a ZenML pipeline object
            component_name:
        """
        # First get the context of the component and its artifacts
        component_context = [c for c in self.store.get_contexts_by_type(
            self.NODE_TYPE_NAME) if c.name.endswith(component_name)][0]
        component_artifacts = self.store.get_artifacts_by_context(
            component_context.id)

        # Second, get the context of the particular pipeline and its artifacts
        pipeline_context = self.store.get_context_by_type_and_name(
            self.RUN_TYPE_NAME, pipeline.pipeline_name)
        pipeline_artifacts = self.store.get_artifacts_by_context(
            pipeline_context.id)

        # Figure out the matching ids
        return [a for a in component_artifacts
                if a.id in [p.id for p in pipeline_artifacts]]

    def get_pipeline_context(self, pipeline):
        # We rebuild context for ml metadata here.
        logger.debug(
            f'Looking for run_id {pipeline.pipeline_name} in metadata store: '
            f'{self.to_config()}')
        run_context = self.store.get_context_by_type_and_name(
            type_name=self.RUN_TYPE_NAME,
            context_name=pipeline.pipeline_name
        )
        if run_context is None:
            raise DoesNotExistException(
                name=pipeline.pipeline_name,
                reason=f'The pipeline does not exist in metadata store '
                       f'because it has not been run yet. Please run the '
                       f'pipeline before trying to fetch artifacts.')
        return run_context
