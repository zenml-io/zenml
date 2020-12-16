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
    query = f'SELECT * FROM `{query_project}.{query_dataset}.{query_table}`'

    if query_limit is not None:
        query += f'\nLIMIT {query_limit}'

    return (pipeline
            | 'ReadFromBigQuery' >> beam_bigquery.ReadFromBigQuery(
                project=dest_project,
                gcs_location=gcs_location,
                query=query,
                use_standard_sql=True))  # TODO: [LOW] Whats this for?


class BQDataStep(BaseDataStep):
    def __init__(self, query_project: Text, query_dataset: Text,
                 query_table: Text, gcs_location: Text,
                 dest_project: Text = None, query_limit: int = None,
                 schema: Dict = None):
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
