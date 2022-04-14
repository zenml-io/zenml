#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from zenml.enums import StackComponentType
from zenml.metadata_stores import MySQLMetadataStore


def test_mysql_metadata_store_attributes():
    """Tests that the basic attributes of the mysql metadata store are set
    correctly."""
    metadata_store = MySQLMetadataStore(
        name="", host="", port=0, database="", username="", password=""
    )
    assert metadata_store.TYPE == StackComponentType.METADATA_STORE
    assert metadata_store.FLAVOR == "mysql"
