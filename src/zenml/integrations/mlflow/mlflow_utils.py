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
"""Implementation of utils specific to the MLflow integration."""

from typing import Optional


def is_databricks_tracking_uri(tracking_uri: Optional[str]) -> bool:
    """Checks whether the given tracking uri is a Databricks tracking uri.

    Args:
        tracking_uri: The tracking uri to check.

    Returns:
        `True` if the tracking uri is a Databricks tracking uri, `False`
        otherwise.
    """
    return tracking_uri == "databricks"


def is_remote_mlflow_tracking_uri(tracking_uri: Optional[str]) -> bool:
    """Checks whether the given tracking uri is remote or not.

    Args:
        tracking_uri: The tracking uri to check.

    Returns:
        `True` if the tracking uri is remote, `False` otherwise.
    """
    if not tracking_uri:
        return False
    return any(
        tracking_uri.startswith(prefix) for prefix in ["http://", "https://"]
    ) or is_databricks_tracking_uri(tracking_uri)
