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
from typing import Text, Dict
from uuid import uuid4

import tensorflow as tf

from zenml.core.repo.repo import Repository
from zenml.core.standards import standard_keys as keys
from zenml.utils import path_utils
from zenml.utils import source_utils
from zenml.utils.enums import GDPComponent
from zenml.utils.post_training.post_training_utils import \
    get_schema_artifact, view_schema, get_feature_spec_from_schema, \
    convert_raw_dataset_to_pandas
from zenml.utils.print_utils import to_pretty_string, PrintStyles
from zenml.utils.zenml_analytics import track, CREATE_DATASOURCE


class BaseDatasource:
    """Base class for all ZenML datasources.

    Every ZenML datasource should override this class.
    """
    DATA_STEP = None
    PREFIX = 'pipeline_'

    @track(event=CREATE_DATASOURCE)
    def __init__(self, name: Text, schema: Dict = None, _id: Text = None,
                 _source: Text = None, *args, **kwargs):
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
            self._source = _source
            self._immutable = True
        else:
            # If none, then this is assumed to be 'new'. Check dupes.
            all_names = Repository.get_instance().get_datasource_names()
            if any(d == name for d in all_names):
                raise Exception(
                    f'Datasource {name} already exists! Please '
                    f'use Repository.get_datasource_by_name("{name}") '
                    f'to fetch.')
            self._id = str(uuid4())
            self._immutable = False
            self._source = source_utils.resolve_source_path(
                self.__class__.__module__ + '.' + self.__class__.__name__
            )

        self.name = name
        self.schema = schema

    def __str__(self):
        return to_pretty_string(self.to_config())

    def __repr__(self):
        return to_pretty_string(self.to_config(), style=PrintStyles.PPRINT)

    @classmethod
    def get_name_from_pipeline_name(cls, pipeline_name: Text):
        return pipeline_name[len(cls.PREFIX)]

    @classmethod
    def from_config(cls, config: Dict):
        """
        Convert from Data Step config to ZenML Datasource object.

        Data step is also populated and configuration set to parameters set
        in the config file.

        Args:
            config: a DataStep config in dict-form (probably loaded from YAML).
        """
        if keys.DataSteps.DATA not in config[keys.GlobalKeys.STEPS]:
            raise Exception("Cant have datasource without data step.")

        # this is the data step config block
        step_config = config[keys.GlobalKeys.STEPS][keys.DataSteps.DATA]
        source = config[keys.GlobalKeys.DATASOURCE][keys.DatasourceKeys.SOURCE]
        datasource_class = source_utils.load_source_path_class(source)
        datasource_name = config[keys.GlobalKeys.DATASOURCE][
            keys.DatasourceKeys.NAME]
        _id = config[keys.GlobalKeys.DATASOURCE][keys.DatasourceKeys.ID]
        return datasource_class(
            name=datasource_name, _id=_id, _source=source,
            **step_config[keys.StepKeys.ARGS])

    def to_config(self):
        """Converts datasource to ZenML config block."""
        return {
            keys.DatasourceKeys.NAME: self.name,
            keys.DatasourceKeys.SOURCE: self._source,
            keys.DatasourceKeys.ID: self._id
        }

    def get_pipeline_name_from_name(self):
        return self.PREFIX + self.name

    def get_data_step(self):
        params = self.__dict__.copy()
        # TODO: [HIGH] Figure out if there is a better way to do this
        params.pop('name')
        params.pop('_id')
        params.pop('_source')
        params.pop('_immutable')
        return self.DATA_STEP(**params)

    def _get_one_pipeline(self):
        """Gets representative pipeline from all pipelines associated."""
        pipelines = \
            Repository.get_instance().get_pipelines_by_datasource(self)

        if len(pipelines) == 0:
            raise Exception('This datasource is not associated with any '
                            'pipelines, therefore there is no data!')
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
        repo: Repository = Repository.get_instance()
        # Take any pipeline and get the datagen
        data_uri = os.path.join(repo.get_artifacts_uri_by_component(
            pipeline.pipeline_name,
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

        spec = get_feature_spec_from_schema(
            pipeline.pipeline_name, GDPComponent.DataSchema.name)

        dataset = tf.data.TFRecordDataset(data_files, compression_type='GZIP')
        return convert_raw_dataset_to_pandas(dataset, spec, sample_size)

    def get_datapoints(self):
        """Gets total number of datapoints in datasource"""
        # TODO: [HIGH] Refactor this
        pipeline = self._get_one_pipeline()
        data_files = self._get_data_file_paths(pipeline)
        return sum(1 for _ in tf.data.TFRecordDataset(data_files,
                                                      compression_type='GZIP'))

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        pipeline = self._get_one_pipeline()
        uri = get_schema_artifact(
            pipeline.pipeline_name, GDPComponent.DataSchema.name)
        view_schema(uri)
