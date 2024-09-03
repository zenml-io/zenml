#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Initialization for the GCP image builder."""

try:
    from zenml.integrations.gcp.image_builders.gcp_image_builder import (
        GCPImageBuilder,
    )

    __all__ = ["GCPImageBuilder"]
except (ImportError, ModuleNotFoundError) as e:
    from zenml.exceptions import IntegrationError
    from zenml.integrations.constants import GCP

    raise IntegrationError(
        f"The `{GCP}` integration that you are trying to use is not "
        "properly installed. Please make sure that you have the correct "
        f"installation with: `zenml integration install {GCP}`"
    )
