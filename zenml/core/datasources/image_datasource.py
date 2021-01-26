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
"""Image Datasource definition"""

from typing import Text

from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.steps.data.image_data_step import ImageDataStep


class ImageDatasource(BaseDatasource):
    """ZenML Image datasource definition.

    Use this for image training pipelines.
    """

    def __init__(self, name: Text = None, base_path='', **unused_kwargs):
        """
        Create a Image datasource.

        Args:
            name (str): Name of datasource
            base_path (str): Path to folder of images
        """
        super().__init__(name, **unused_kwargs)
        self.base_path = base_path

    def get_data_step(self):
        return ImageDataStep(self.base_path)
