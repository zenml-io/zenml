#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of ZenML's pandas materializer."""

from zenml.integrations.pandas.materializers.pandas_materializer import (  # noqa
    PandasMaterializer,
)
from zenml.logger import get_logger

# TODO: We will need to write a migration for older materializer source entries
get_logger(__name__).warning(
    "The ZenML built-in Pandas materializer has been moved to an "
    "integration. Before you use it, make sure you that the `pandas` "
    "integration is installed with `zenml integration install pandas`, and if "
    "you need to import the materializer explicitly, please use: "
    "'from zenml.integrations.pandas.materializers import PandasMaterializer'"
)
