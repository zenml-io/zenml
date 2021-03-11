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

from typing import Text

from tfx.orchestration import metadata

from zenml.metadata import ZenMLMetadataStore
from zenml.enums import MLMetadataTypes


class MySQLMetadataStore(ZenMLMetadataStore):
    STORE_TYPE = MLMetadataTypes.mysql.name

    def __init__(self, host: Text, port: int, database: Text, username: Text,
                 password: Text):
        """Constructor for MySQL MetadataStore for ZenML"""
        self.host = host
        self.port = int(port)  # even if its a string, it should be casted
        self.database = database
        self.username = username
        self.password = password
        super().__init__()

    def get_tfx_metadata_config(self):
        return metadata.mysql_metadata_connection_config(
            host=self.host,
            port=self.port,
            database=self.database,
            username=self.username,
            password=self.password)
