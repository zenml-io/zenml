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
"""Pipeline to create data sources"""

from typing import Dict, Text, Any, List

from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen

from zenml.components import DataGen
from zenml.enums import GDPComponent
from zenml.pipelines import BasePipeline
from zenml.utils.post_training.post_training_utils import \
    view_statistics, view_schema


class DataPipeline(BasePipeline):
    """DataPipeline definition to create datasources.

    A DataPipeline is used to create datasources in ZenML. Each data pipeline
    creates a snapshot of the datasource in time. All datasources are consumed
    by different ZenML pipelines like the TrainingPipeline.
    """
    PIPELINE_TYPE = 'data'

    def get_tfx_component_list(self, config: Dict[Text, Any]) -> List:
        """
        Creates a data pipeline out of TFX components.

        A data pipeline is used to ingest data from a configured source, e.g.
        local files or cloud storage. In addition, a schema and statistics are
        also computed immediately afterwards for the processed data points.

        Args:
            config: Dict. Contains a ZenML configuration used to build the
             data pipeline.

        Returns:
            A list of TFX components making up the data pipeline.
        """
        data = DataGen(
            name=self.datasource.name,
            source=self.datasource._source,
            source_args=self.datasource._source_args).with_id(
            GDPComponent.DataGen.name
        )
        statistics_data = StatisticsGen(
            examples=data.outputs.examples
        ).with_id(GDPComponent.DataStatistics.name)

        schema_data = SchemaGen(
            statistics=statistics_data.outputs.output,
        ).with_id(GDPComponent.DataSchema.name)

        return [data, statistics_data, schema_data]

    def view_statistics(self, magic: bool = False, port: int = 0):
        """
        View statistics for data pipeline in HTML.

        Args:
            magic (bool): Creates HTML page if False, else
            creates a notebook cell.
            port (int): Port at which to launch the statistics facet.
        """
        uri = self.get_artifacts_uri_by_component(
            GDPComponent.DataStatistics.name)[0]
        view_statistics(uri, magic, port)

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        uri = self.get_artifacts_uri_by_component(
            GDPComponent.DataSchema.name)[0]
        view_schema(uri)

    def steps_completed(self) -> bool:
        return True
