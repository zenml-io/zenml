#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation of ZenML's numpy materializer."""

# With the code below, we keep a reference to the NumpyMaterializer in its
# original spot. So, if someone has an artifact version that was created with
# the NumpyMaterializer, (assuming that they have it installed), they will still
# be able to use the artifact version. However, if this file is to be removed,
# you have to write a DB migration script to change the materializer source
# of the old artifact version entries.

from zenml.exceptions import IntegrationError

try:
    from zenml.integrations.numpy.materializers.numpy_materializer import (  # noqa
        NumpyMaterializer,
    )
except (ImportError, ModuleNotFoundError) as e:
    raise IntegrationError(
        "The ZenML built-in Numpy materializer has been moved to an "
        "integration. Before you use it, make sure you that the `numpy` "
        "integration is installed with `zenml integration install numpy`, "
        "and if you need to import the materializer explicitly, please use: "
        "'from zenml.integrations.numpy.materializers import "
        f"NumpyMaterializer': {e}"
    )
