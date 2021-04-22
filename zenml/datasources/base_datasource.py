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
from pathlib import Path
from typing import Text, Dict, Optional, Callable
from uuid import uuid4

import tensorflow as tf

from zenml.enums import GDPComponent
from zenml.exceptions import AlreadyExistsException
from zenml.exceptions import EmptyDatasourceException
from zenml.logger import get_logger
from zenml.metadata import ZenMLMetadataStore
from zenml.repo import Repository, ArtifactStore
from zenml.standards import standard_keys as keys
from zenml.utils import path_utils
from zenml.utils import source_utils
from zenml.utils.analytics_utils import CREATE_DATASOURCE
from zenml.utils.analytics_utils import track
from zenml.utils.post_training.post_training_utils import \
    view_schema, get_feature_spec_from_schema, \
    convert_raw_dataset_to_pandas, view_statistics
from zenml.utils.print_utils import to_pretty_string, PrintStyles

logger = get_logger(__name__)


class BaseDatasource:
    """Base class for all ZenML datasources.
    Every ZenML datasource should override this class.
    """

    def __init__(
            self,
            name: Text,
            _id: Text = None,
            backend=None,
            metadata_store: Optional[ZenMLMetadataStore] = None,
            artifact_store: Optional[ArtifactStore] = None,
            commits: Optional[Dict] = None,
            *args,
            **kwargs):
        """
        Construct the datasource.

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

        # Metadata store
        if metadata_store:
            self.metadata_store: ZenMLMetadataStore = metadata_store
        else:
            # use default
            self.metadata_store: ZenMLMetadataStore = \
                Repository.get_instance().get_default_metadata_store()

        # Default to local
        if backend is None:
            from zenml.backends.orchestrator import OrchestratorBaseBackend
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

        if commits is None:
            self.commits = {}
        else:
            self.commits = commits

        self.name = name
        self._immutable = False
        self._source = source_utils.resolve_class(self.__class__)
        self._source_args = kwargs

    def __str__(self):
        return to_pretty_string(self.to_config())

    def __repr__(self):
        return to_pretty_string(self.to_config(), style=PrintStyles.PPRINT)

    @property
    def is_empty(self):
        if self.commits:
            return False
        return True

    @property
    def n_datapoints(self):
        """Gets total number of datapoints in datasource"""
        pipeline = self._get_one_pipeline()
        data_files = self._get_data_file_paths(pipeline)
        return sum(1 for _ in tf.data.TFRecordDataset(data_files,
                                                      compression_type='GZIP'))

    @abstractmethod
    def process(self, output_path: Text, make_beam_pipeline: Callable = None):
        pass

    def commit(self):
        from zenml.pipelines.data_pipeline import DataPipeline
        data_pipeline = DataPipeline(
            enable_cache=False,
            backend=self.backend,
            metadata_store=self.metadata_store,
            artifact_store=self.artifact_store,
            datasource=self
        )
        data_pipeline.run()
        commit_id = data_pipeline.pipeline_name.split('_')[2]
        self.commits[commit_id] = data_pipeline.pipeline_name.split('_')[1]
        return commit_id

    @classmethod
    def from_config(cls, config: Dict):
        """
        Convert from Data Step config to ZenML Datasource object.
        Data step is also populated and configuration set to parameters set
        in the config file.
        Args:
            config: a DataStep config in dict-form (probably loaded from YAML).
        """
        if keys.DatasourceKeys.SOURCE not in config[
            keys.PipelineKeys.DATASOURCE]:
            return None  # can be empty

        # this is the data step config block
        source = config[keys.PipelineKeys.DATASOURCE][
            keys.DatasourceKeys.SOURCE]
        datasource_class = source_utils.load_source_path_class(source)
        datasource_name = config[keys.PipelineKeys.DATASOURCE][
            keys.DatasourceKeys.NAME]
        _id = config[keys.PipelineKeys.DATASOURCE][keys.DatasourceKeys.ID]
        args = config[keys.PipelineKeys.DATASOURCE][keys.DatasourceKeys.ARGS]

        # resolve commits
        repo: Repository = Repository.get_instance()
        # TODO [HIGH]: Ugly hack to get around circular dependencies. We
        #  need to find which data pipelines are associated with this
        #  pipeline so we first find all associated pipelines and then
        #  filter by the 'data' type.
        from zenml.pipelines.data_pipeline import DataPipeline
        data_pipeline_paths = [x for x in
                               repo.get_pipeline_f_paths_by_datasource_id(_id)]
        data_pipeline_names = [Path(x).stem for x in data_pipeline_paths if
                               Path(x).stem.startswith(
                                   DataPipeline.PIPELINE_TYPE)]

        # Another ugly hack to recompile the commit times
        commits = {x.split('_')[2]: x.split('_')[1] for x in
                   data_pipeline_names}

        # Resolve the stores and backend. All pipelines will have the same.
        artifact_store, metadata_store, backend = None, None, None
        if data_pipeline_names:
            artifact_store = repo.get_artifact_store_from_file_path(
                data_pipeline_paths[0])
            metadata_store = repo.get_metadata_store_from_file_path(
                data_pipeline_paths[0])
            backend = repo.get_orchestrator_backend_from_file_path(
                data_pipeline_paths[0])

        obj = datasource_class(
            name=datasource_name, _id=_id, commits=commits, backend=backend,
            metadata_store=metadata_store, artifact_store=artifact_store,
            **args)
        obj._immutable = True
        return obj

    def to_config(self):
        """Converts datasource to ZenML config block."""
        return {
            keys.DatasourceKeys.NAME: self.name,
            keys.DatasourceKeys.SOURCE: self._source,
            keys.DatasourceKeys.ARGS: self._source_args,
            keys.DatasourceKeys.ID: self._id,
        }

    def get_latest_commit(self):
        a = [k for k, v in
             sorted(self.commits.items(), key=lambda item: item[1])]
        if a:
            return a[-1]

    def get_first_commit(self):
        a = [k for k, v in
             sorted(self.commits.items(), key=lambda item: item[1])]
        if a:
            return a[0]

    def get_data_pipeline_from_commit(self, commit_id: Text):
        from zenml.pipelines.data_pipeline import DataPipeline

        if commit_id not in self.commits:
            raise AssertionError(
                f'There is no such commit_id as {commit_id} in the '
                f'datasource {self.name}')

        repo: Repository = Repository.get_instance()
        name = DataPipeline.get_name_from_pipeline_name(
            DataPipeline.PIPELINE_TYPE + '_' + self.commits[
                commit_id] + '_' + commit_id)
        return repo.get_pipeline_by_name(name)

    def _get_one_pipeline(self):
        """Gets representative pipeline from all pipelines associated."""
        if self.commits:
            return self.get_data_pipeline_from_commit(
                list(self.commits.keys())[0])
        raise EmptyDatasourceException

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

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        pipeline = self._get_one_pipeline()
        uri = pipeline.get_artifacts_uri_by_component(
            GDPComponent.DataSchema.name)[0]
        view_schema(uri)

    def view_statistics(self, port):
        """
        View statistics of data flowing in pipeline.

        Args:
            port (int): Port at which to launch the statistics facet.
        """
        pipeline = self._get_one_pipeline()
        uri = pipeline.get_artifacts_uri_by_component(
            GDPComponent.DataStatistics.name)[0]
        view_statistics(uri, port=port)
