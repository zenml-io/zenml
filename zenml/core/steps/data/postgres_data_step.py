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
"""Base interface for Postgres Data Step"""

from typing import Text, Any, Dict

import apache_beam as beam
from beam_nuggets.io import relational_db

from zenml.core.steps.data.base_data_step import BaseDataStep


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
def ReadFromPostgres(
        p: beam.Pipeline,
        username: Text,
        password: Text,
        database: Text,
        table: Text,
        host: Text = 'localhost',
        port: int = 5432,
        query_limit: int = None,
        schema: Dict = None,
    ) -> beam.pvalue.PCollection:
    """
    The Beam PTransform used to read data from a specific BQ table.

    Args:
        p: Input beam.Pipeline object coming from a TFX Executor.
        host: Host of database.
        username: Username of database user.
        password: Password to connect to database.
        port: Port to connect to with database (default 5432)
        database: Name of the target database.
        table: Name of the target table.
        query_limit: Max number of rows to fetch.
        schema: Dict specifying schema.

    Returns:
        A beam.PCollection of data points. Each row in the BigQuery table
         represents a single data point.
    """
    query = f'SELECT * FROM {table}'

    if query_limit is not None:
        query += f'\nLIMIT {query_limit}'

    source_config = relational_db.SourceConfiguration(
        drivername='postgresql+pg8000',
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
    )
    records = p | "Reading records from db" >> relational_db.ReadFromDB(
        source_config=source_config,
        table_name=table,
        query=query,
    )
    return records


class PostgresDataStep(BaseDataStep):
    """
    A step that reads in data from a Google BigQuery table supplied on
    construction.
    """

    def __init__(self,
                 username: Text,
                 password: Text,
                 database: Text,
                 table: Text,
                 host: Text = 'localhost',
                 port: int = 5432,
                 query_limit: int = None,
                 schema: dict = None,
                 ):
        """
        Postgres data step constructor. Targets a single Postgres table.

        Args:
            host: Host of database.
            username: Username of database user.
            password: Password to connect to database.
            port: Port to connect to with database (default 5432)
            database: Name of the target database.
            table: Name of the target table.
            query_limit: Max number of rows to fetch.
            schema: Dict specifying schema.
        """
        super().__init__(
            username=username,
            password=password,
            database=database,
            table=table,
            host=host,
            port=port,
            query_limit=query_limit,
            schema=schema
        )
        self.username = username
        self.password = password
        self.database = database
        self.table = table
        self.host = host
        self.port = port
        self.query_limit = query_limit

    def read_from_source(self):
        return ReadFromPostgres(
            username=self.username,
            password=self.password,
            database=self.database,
            table=self.table,
            host=self.host,
            port=self.port,
            query_limit=self.query_limit,
        )
