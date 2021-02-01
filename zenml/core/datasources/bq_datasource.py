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
"""BigQuery Datasource definition"""

from typing import Text, Optional, Dict

from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.steps.data.bq_data_step import BQDataStep


class BigQueryDatasource(BaseDatasource):
    """ZenML BigQuery datasource definition.

    Use this for BigQuery training pipelines.
    """

    def __init__(self,
                 name: Text,
                 query_project: Text,
                 query_dataset: Text,
                 query_table: Text,
                 gcs_location: Text,
                 query_limit: Optional[int] = None,
                 dest_project: Text = None,
                 schema: Dict = None, **unused_kwargs):
        """
        Initialize BigQuery source. This creates a DataPipeline that
        essentially performs the following query using Apache Beam.

        `SELECT * FROM query_project.query_dataset.query_table`

        A Google Cloud Storage location needs to be provided to make this work.
        The GCS location is used to write temporary dumps of the query as the
        beam pipeline executes. The location must exist within a GCP project
        specified through dest_project.

        Args:
            name: name of datasource. Must be globally unique in the repo.
            query_project: name of gcp project.
            query_dataset: name of dataset.
            query_table: name of table in dataset.
            query_limit: how many rows, from the top, to be queried.
            gcs_location: google cloud storage (bucket) location to store temp.
            dest_project: name of destination project. If None is specified,
            then dest_project is set to the same as query_project.
        """
        super().__init__(name, schema, **unused_kwargs)

        # Check whether gcs_location is a valid one
        if not gcs_location.startswith('gs://'):
            Exception(f'{gcs_location} is not a valid GCS path. It must start '
                      f'with a gs://')

        self.query_project = query_project
        self.query_dataset = query_dataset
        self.query_table = query_table
        self.query_limit = query_limit
        self.gcs_location = gcs_location

        # If dest project not given, we use the same as query project
        self.dest_project = dest_project if dest_project else query_project

    def get_data_step(self):
        return BQDataStep(
            query_project=self.query_project,
            query_dataset=self.query_dataset,
            query_table=self.query_table,
            gcs_location=self.gcs_location,
            dest_project=self.dest_project,
            query_limit=self.query_limit,
            schema=self.schema
        )
