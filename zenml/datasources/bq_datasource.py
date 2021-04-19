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

from typing import Optional, Callable
from typing import Text, Dict

from apache_beam.io.gcp import bigquery as beam_bigquery

from zenml.datasources import BaseDatasource
from zenml.utils.beam_utils import WriteToTFRecord


class BigQueryDatasource(BaseDatasource):
    """ZenML BigQuery datasource definition.

    Use this for BigQuery training pipelines.
    """

    def __init__(
            self,
            name: Text,
            query_project: Text,
            query_dataset: Text,
            query_table: Text,
            gcs_location: Text,
            query_limit: Optional[int] = None,
            dest_project: Text = None,
            schema: Dict = None,
            **kwargs):
        """
        Initialize BigQuery source. This creates a datasource that
        essentially reflects the following query using Apache Beam.

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
            schema (str): optional schema for data to conform to.
        """
        # Check whether gcs_location is a valid one
        if not gcs_location.startswith('gs://'):
            Exception(f'{gcs_location} is not a valid GCS path. It must start '
                      f'with a gs://')

        self.query_project = query_project
        self.query_dataset = query_dataset
        self.query_table = query_table
        self.query_limit = query_limit
        self.gcs_location = gcs_location
        self.schema = schema

        # If dest project not given, we use the same as query project
        self.dest_project = dest_project if dest_project else query_project

        super().__init__(
            name,
            query_project=self.query_project,
            query_dataset=self.query_dataset,
            query_table=self.query_table,
            gcs_location=self.gcs_location,
            query_limit=self.query_limit,
            dest_project=self.dest_project,
            schema=self.schema,
            **kwargs
        )

    def process(self, output_path: Text, make_beam_pipeline: Callable = None):
        query = f'SELECT * FROM `{self.query_project}.{self.query_dataset}.' \
                f'{self.query_table}`'

        if self.query_limit is not None:
            query += f'\nLIMIT {self.query_limit}'

        with make_beam_pipeline() as p:
            (p
             | 'ReadFromBigQuery' >> beam_bigquery.ReadFromBigQuery(
                        project=self.dest_project,
                        gcs_location=self.gcs_location,
                        query=query,
                        use_standard_sql=True)
             | WriteToTFRecord(self.schema, output_path)
             )
