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

import os
from abc import abstractmethod
from typing import Text, Dict
from uuid import uuid4

import tensorflow as tf

from zenml.core.repo.repo import Repository
from zenml.core.standards import standard_keys as keys
from zenml.utils import path_utils
from zenml.utils import source_utils
from zenml.utils.enums import GDPComponent
from zenml.utils.exceptions import EmptyDatasourceException
from zenml.utils.logger import get_logger
from zenml.utils.post_training.post_training_utils import \
    view_schema, get_feature_spec_from_schema, \
    convert_raw_dataset_to_pandas, view_statistics
from zenml.utils.print_utils import to_pretty_string, PrintStyles
from zenml.utils.zenml_analytics import track, CREATE_DATASOURCE
from zenml.utils.exceptions import AlreadyExistsException

logger = get_logger(__name__)


class BaseDatasource:
    """Base class for all ZenML datasources.

    Every ZenML datasource should override this class.
    """

    def __init__(self,
                 name: Text,
                 schema: Dict = None,
                 _id: Text = None,
                 *args, **kwargs):
        """
        Construct the datasource

        Args:
            name (str): name of datasource
            schema (dict): schema of datasource
            _id: unique ID (for internal use)
        """
        if _id:
            # Its loaded from config
            self._id = _id
            logger.debug(f'Datasource {name} loaded.')
        else:
            # If none, then this is assumed to be 'new'. Check dupes.
            all_names = Repository.get_instance().get_datasource_names()
            if any(d == name for d in all_names):
                raise AlreadyExistsException(
                    name=name,
                    resource_type='datasource')
            self._id = str(uuid4())
            track(event=CREATE_DATASOURCE)
            logger.info(f'Datasource {name} created.')

        self.name = name
        self.schema = schema
        self._immutable = False
        self._source = source_utils.resolve_source_path(
            self.__class__.__module__ + '.' + self.__class__.__name__
        )

    def __str__(self):
        return to_pretty_string(self.to_config())

    def __repr__(self):
        return to_pretty_string(self.to_config(), style=PrintStyles.PPRINT)

    @classmethod
    def from_config(cls, config: Dict):
        """
        Convert from Data Step config to ZenML Datasource object.

        Data step is also populated and configuration set to parameters set
        in the config file.

        Args:
            config: a DataStep config in dict-form (probably loaded from YAML).
        """
        if keys.DataSteps.DATA not in config[keys.PipelineKeys.STEPS]:
            return None  # can be empty

        # this is the data step config block
        step_config = config[keys.PipelineKeys.STEPS][keys.DataSteps.DATA]
        source = config[keys.PipelineKeys.DATASOURCE][
            keys.DatasourceKeys.SOURCE]
        datasource_class = source_utils.load_source_path_class(source)
        datasource_name = config[keys.PipelineKeys.DATASOURCE][
            keys.DatasourceKeys.NAME]
        _id = config[keys.PipelineKeys.DATASOURCE][keys.DatasourceKeys.ID]
        obj = datasource_class(
            name=datasource_name, _id=_id, _source=source,
            **step_config[keys.StepKeys.ARGS])
        obj._immutable = True
        return obj

    def to_config(self):
        """Converts datasource to ZenML config block."""
        return {
            keys.DatasourceKeys.NAME: self.name,
            keys.DatasourceKeys.SOURCE: self._source,
            keys.DatasourceKeys.ID: self._id
        }

    @abstractmethod
    def get_data_step(self):
        pass

    def _get_one_pipeline(self):
        """Gets representative pipeline from all pipelines associated."""
        pipelines = \
            Repository.get_instance().get_pipelines_by_datasource(self)

        if len(pipelines) == 0:
            raise EmptyDatasourceException
        return pipelines[0]

    def _get_data_file_paths(self, pipeline):
        """
        Gets path where data is stored as list of file paths.

        Args:
            pipeline: a pipeline with this datasource embedded
        """
        if pipeline.datasource._id != self._id:
            raise AssertionError('This pipeline does not belong to this '
                                 'datasource.')
        # Take any pipeline and get the datagen
        data_uri = os.path.join(pipeline.get_artifacts_uri_by_component(
            GDPComponent.DataGen.name
        )[0], 'examples')
        data_files = path_utils.list_dir(data_uri)
        return data_files

    def sample_data(self, sample_size: int = 100000):
        """
        Sampels data from datasource as a pandas DataFrame.

        Args:
            sample_size: # of rows to sample.
        """
        pipeline = self._get_one_pipeline()
        data_files = self._get_data_file_paths(pipeline)

        schema_uri = pipeline.get_artifacts_uri_by_component(
            GDPComponent.DataSchema.name)[0]
        spec = get_feature_spec_from_schema(schema_uri)

        dataset = tf.data.TFRecordDataset(data_files, compression_type='GZIP')
        return convert_raw_dataset_to_pandas(dataset, spec, sample_size)

    def get_datapoints(self):
        """Gets total number of datapoints in datasource"""
        pipeline = self._get_one_pipeline()
        data_files = self._get_data_file_paths(pipeline)
        return sum(1 for _ in tf.data.TFRecordDataset(data_files,
                                                      compression_type='GZIP'))

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        pipeline = self._get_one_pipeline()
        uri = pipeline.get_artifacts_uri_by_component(
            GDPComponent.DataSchema.name)[0]
        view_schema(uri)

    def view_statistics(self):
        """View statistics of data flowing in pipeline."""
        pipeline = self._get_one_pipeline()
        uri = pipeline.get_artifacts_uri_by_component(
            GDPComponent.DataStatistics.name)[0]
        view_statistics(uri)
