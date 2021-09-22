#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

from ml_metadata.proto import metadata_store_pb2

from zenml.core.component_factory import metadata_store_factory
from zenml.enums import MLMetadataTypes
from zenml.metadata.base_metadata_store import BaseMetadataStore


@metadata_store_factory.register(MLMetadataTypes.mock)
class MockMetadataStore(BaseMetadataStore):
    """Mock metadata store."""

    def get_tfx_metadata_config(self):
        """Return tfx metadata config for mock metadata store."""
        config = metadata_store_pb2.ConnectionConfig()
        config.fake_database.SetInParent()  # Sets an empty fake
        return config
