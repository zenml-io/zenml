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

from zenml.core.components.data_gen import constants
# from zenml.core.components.data_gen.sources.bq import BigQuerySource
from zenml.core.components.data_gen.sources.local_image import LocalImageSource
from zenml.core.components.data_gen.sources.gcs_image import GCSImageSource
from zenml.core.components.data_gen.sources.local_csv import LocalCSVSource
# from zenml.core.components.data_gen.sources.gcs_csv import GCSCSVSource


class SourceFactory:

    def __init__(self):
        self.sources = {}

    def get_sources(self):
        return self.sources

    def get_single_source(self, key):
        """
        Args:
            key:
        """
        return self.sources[key]

    def register_source(self, key, source):
        """
        Args:
            key:
            source:
        """
        self.sources[key] = source


# Register the injections into the factory
source_factory = SourceFactory()
# source_factory.register_source(constants.SOURCE_BQ, BigQuerySource)
source_factory.register_source(constants.SOURCE_LOCAL_IMAGE, LocalImageSource)
source_factory.register_source(constants.SOURCE_GCS_IMAGE, GCSImageSource)
source_factory.register_source(constants.SOURCE_LOCAL_CSV, LocalCSVSource)
# source_factory.register_source(constants.SOURCE_GCS_CSV, GCSCSVSource)
