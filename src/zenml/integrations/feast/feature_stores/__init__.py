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
"""Feast Feature Store integration for ZenML.

Feature stores allow data teams to serve data via an offline store and an online
low-latency store where data is kept in sync between the two. It also offers a
centralized registry where features (and feature schemas) are stored for use
within a team or wider organization. Feature stores are a relatively recent
addition to commonly-used machine learning stacks. Feast is a leading
open-source feature store, first developed by Gojek in collaboration with
Google.
"""

try:
    from zenml.integrations.feast.feature_stores.feast_feature_store import (  # noqa
        FeastFeatureStore,
    )

    __all__ = ["FeastFeatureStore"]
except (ImportError, ModuleNotFoundError) as e:
    from zenml.exceptions import IntegrationError
    from zenml.integrations.constants import FEAST

    raise IntegrationError(
        f"The `{FEAST}` integration that you are trying to use is not "
        "properly installed. Please make sure that you have the correct "
        f"installation with: `zenml integration install {FEAST}`"
    )
