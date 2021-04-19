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

from typing import Callable
from typing import Text, Dict

from beam_nuggets.io import relational_db

from zenml.datasources import BaseDatasource
from zenml.utils.beam_utils import WriteToTFRecord


class PostgresDatasource(BaseDatasource):
    """ZenML Postgres datasource definition.

    Use this for pipelines sourcing directly from a Postgres database table.
    """

    def __init__(
            self,
            name: Text,
            username: Text,
            password: Text,
            database: Text,
            table: Text,
            host: Text = 'localhost',
            port: int = 5432,
            query_limit: int = None,
            schema: Dict = None,
            **kwargs):
        """
        Initialize Postgres source. This creates a DataPipeline that
        essentially performs the following query using Apache Beam.

        `SELECT * FROM dataset.table LIMIT query_limit`
        Args:
            name: Name of datasource.
            username: Username of database user.
            password: Password to connect to database.
            database: Name of the target database.
            table: Name of the target table.
            host: Host of database.
            port: Port to connect to with database (default 5432)
            query_limit: Max number of rows to fetch.
            schema: Dict specifying schema.
        """
        self.username = username
        self.password = password
        self.database = database
        self.table = table
        self.host = host
        self.port = port
        self.query_limit = query_limit
        self.schema = schema

        super().__init__(
            name,
            username=self.username,
            password=self.password,
            database=self.database,
            table=self.table,
            host=self.host,
            port=self.port,
            query_limit=self.query_limit,
            schema=self.schema,
            **kwargs
        )

    def process(self, output_path: Text, make_beam_pipeline: Callable = None):
        query = f'SELECT * FROM {self.table}'

        if self.query_limit is not None:
            query += f'\nLIMIT {self.query_limit}'

        source_config = relational_db.SourceConfiguration(
            drivername='postgresql+pg8000',
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            database=self.database,
        )

        with make_beam_pipeline() as p:
            p | "Reading Postgres" >> relational_db.ReadFromDB(
                source_config=source_config,
                table_name=self.table,
                query=query) \
            | WriteToTFRecord(self.schema, output_path)
