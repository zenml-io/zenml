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
"""Postgres Datasource definition"""

from typing import Text, Dict

from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.steps.data.postgres_data_step import PostgresDataStep


class PostgresDatasource(BaseDatasource):
    """ZenML Postgres datasource definition.

    Use this for Postgres training pipelines.
    """

    def __init__(self,
                 name: Text,
                 username: Text,
                 password: Text,
                 database: Text,
                 table: Text,
                 host: Text = 'localhost',
                 port: int = 5432,
                 query_limit: int = None,
                 schema: Dict = None, **unused_kwargs):
        """
        Initialize Postgres source. This creates a DataPipeline that
        essentially performs the following query using Apache Beam.

        `SELECT * FROM dataset.table LIMIT query_limit`
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

        self.username = username
        self.password = password
        self.database = database
        self.table = table
        self.host = host
        self.port = port
        self.query_limit = query_limit
        self.schema = schema

    def get_data_step(self):
        return PostgresDataStep(
            username=self.username,
            password=self.password,
            database=self.database,
            table=self.table,
            host=self.host,
            port=self.port,
            query_limit=self.query_limit,
            schema=self.schema,
        )
