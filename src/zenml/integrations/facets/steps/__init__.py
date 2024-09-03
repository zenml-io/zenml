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
"""Facets Standard Steps."""

try:
    from zenml.integrations.facets.models import FacetsComparison
    from zenml.integrations.facets.steps.facets_visualization_steps import (
        facets_visualization_step,
        facets_dict_visualization_step,
        facets_list_visualization_step,
    )

    __all__ = [
        "facets_visualization_step",
        "facets_dict_visualization_step",
        "facets_list_visualization_step",
        "FacetsComparison",
    ]
except (ImportError, ModuleNotFoundError) as e:
    from zenml.exceptions import IntegrationError
    from zenml.integrations.constants import FACETS

    raise IntegrationError(
        f"The `{FACETS}` integration that you are trying to use is not "
        "properly installed. Please make sure that you have the correct "
        f"installation with: `zenml integration install {FACETS}`"
    )
