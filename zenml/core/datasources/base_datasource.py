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
"""Base Class for all ZenML datasources"""

from typing import Text, Optional, List, Type, Dict

from zenml.core.backends.base_backend import BaseBackend
from zenml.core.metadata.metadata_wrapper import ZenMLMetadataStore
from zenml.core.repo.artifact_store import ArtifactStore
from zenml.utils.enums import PipelineStatusTypes
from zenml.utils.zenml_analytics import track, CREATE_DATASOURCE


class BaseDatasource:
    """Base class for all ZenML datasources.

    Every ZenML datasource should override this class.
    """
    DATA_STEP = None

    @track(event=CREATE_DATASOURCE)
    def __init__(self, name: Text, schema: Dict = None, *args, **kwargs):
        """
        Construct the datasource

        Args:
            name (str): name of datasource
        """
        self.name = name
        self.schema = schema
        self.data_pipeline = None

    def _create_pipeline_name(self):
        return 'pipeline_' + self.name

    def get_name_from_pipeline_name(self, pipeline_name: Text):
        return pipeline_name.replace('pipeline_', '')

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
        # Use everything in constructor to create data step
        from zenml.core.pipelines.data_pipeline import DataPipeline
        self.data_pipeline = DataPipeline(self._create_pipeline_name())

        params = self.__dict__.copy()
        # TODO: [HIGH] Figure out if there is a better way to do this
        params.pop('data_pipeline')
        params.pop('name')
        data_step = self.DATA_STEP(**params)
        self.data_pipeline.add_data_step(data_step)

        # TODO: Temporary
        from zenml.core.steps.split.categorical_split_step import CategoricalDomainSplitStep
        self.data_pipeline.add_split_step(CategoricalDomainSplitStep(
            categorical_column='payment_type',
            split_map={'train': ['Cash'], 'nicholasisdaman': ['Credit Card']}
        ))

        self.data_pipeline.run(backends, metadata_store, artifact_store)

    def has_run(self) -> bool:
        """Returns true if datasource's pipeline has finished successfully."""
        if self.data_pipeline:
            return self.data_pipeline.get_status() == \
                   PipelineStatusTypes.Succeeded.name
        return False
