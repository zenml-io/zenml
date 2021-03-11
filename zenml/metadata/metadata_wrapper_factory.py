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
"""Factory to register metadata_wrapper classes to metadata_wrappers"""

from zenml.metadata import MockMetadataStore
from zenml.metadata import MySQLMetadataStore
from zenml.metadata import SQLiteMetadataStore


class MetadataWrapperFactory:
    """Definition of MetadataWrapperFactory to track all metadata_wrappers.

    All metadata_wrappers (including custom metadata_wrappers) are to be
    registered here.
    """

    def __init__(self):
        self.metadata_wrappers = {}

    def get_metadata_wrappers(self):
        return self.metadata_wrappers

    def get_single_metadata_wrapper(self, key):
        return self.metadata_wrappers[key]

    def register_metadata_wrapper(self, key, metadata_wrapper_):
        self.metadata_wrappers[key] = metadata_wrapper_


# Register the injections into the factory
wrapper_factory = MetadataWrapperFactory()
wrapper_factory.register_metadata_wrapper(SQLiteMetadataStore.STORE_TYPE,
                                          SQLiteMetadataStore)
wrapper_factory.register_metadata_wrapper(MySQLMetadataStore.STORE_TYPE,
                                          MySQLMetadataStore)
wrapper_factory.register_metadata_wrapper(MockMetadataStore.STORE_TYPE,
                                          MockMetadataStore)
