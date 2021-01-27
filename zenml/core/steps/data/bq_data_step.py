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
"""Base interface for BQ Data Step"""

from typing import Text, Any, Dict

import apache_beam as beam
from apache_beam.io.gcp import bigquery as beam_bigquery

from zenml.core.steps.data.base_data_step import BaseDataStep


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
def ReadFromBigQuery(pipeline: beam.Pipeline,
                     query_project: Text,
                     query_dataset: Text,
                     query_table: Text,
                     gcs_location: Text,
                     dest_project: Text,
                     query_limit: int = None) -> beam.pvalue.PCollection:
    """
    The Beam PTransform used to read data from a specific BQ table.

    Args:
        pipeline: Input beam.Pipeline object coming from a TFX Executor.
        query_project: Google Cloud project where the target table is
         located.
        query_dataset: Google Cloud project where the target dataset is
         located.
        query_table: Name of the target BigQuery table.
        gcs_location: Name of the Google Cloud Storage bucket where
         the extracted table should be written as a string.
        dest_project: Additional Google Cloud Project identifier.
        query_limit: Optional, maximum limit of how many datapoints
         to read from the specified BQ table.

    Returns:
        A beam.PCollection of data points. Each row in the BigQuery table
         represents a single data point.

    """
    query = f'SELECT * FROM `{query_project}.{query_dataset}.{query_table}`'

    if query_limit is not None:
        query += f'\nLIMIT {query_limit}'

    return (pipeline
            | 'ReadFromBigQuery' >> beam_bigquery.ReadFromBigQuery(
                project=dest_project,
                gcs_location=gcs_location,
                query=query,
                use_standard_sql=True))


class BQDataStep(BaseDataStep):
    """
    A step that reads in data from a Google BigQuery table supplied on
    construction.
    """

    def __init__(self,
                 query_project: Text,
                 query_dataset: Text,
                 query_table: Text,
                 gcs_location: Text,
                 dest_project: Text = None,
                 query_limit: int = None,
                 schema: Dict = None):
        """
        BigQuery (BQ) data step constructor. Targets a single BigQuery table
        within a public or private project and dataset. In order to use
        private BQ tables in your pipelines, you may be required to set the
        GOOGLE_APPLICATION_CREDENTIALS environment variable within your code,
        e.g. like so:

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/file.json",

        pointing to a valid service account file for your project and dataset
        that has the necessary permissions.

        Args:
            query_project: Google Cloud project where the target table
             is located.
            query_dataset: Google Cloud project where the target dataset
             is located.
            query_table: Name of the target BigQuery table.
            gcs_location: Name of the Google Cloud Storage bucket where the
             extracted table should be written as a string.
            dest_project: Additional Google Cloud Project identifier.
            query_limit: Optional, maximum limit of how many datapoints
             to read from the specified BQ table.
            schema: Optional schema providing data type information about
             the data source.
        """
        super().__init__(schema=schema,
                         query_project=query_project,
                         query_dataset=query_dataset,
                         query_table=query_table,
                         gcs_location=gcs_location,
                         dest_project=dest_project,
                         query_limit=query_limit)
        self.query_project = query_project
        self.query_dataset = query_dataset
        self.query_table = query_table
        self.dest_project = dest_project
        self.query_limit = query_limit
        self.gcs_location = gcs_location

    def read_from_source(self):
        return ReadFromBigQuery(
            query_project=self.query_project,
            query_dataset=self.query_dataset,
            query_table=self.query_table,
            dest_project=self.dest_project,
            query_limit=self.query_limit,
            gcs_location=self.gcs_location,
        )
