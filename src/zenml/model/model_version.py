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
"""DEPRECATED, use `from zenml import Model` instead."""

from typing import Any

from zenml.logger import get_logger
from zenml.model.model import Model

logger = get_logger(__name__)


# TODO: deprecate me
class ModelVersion(Model):
    """DEPRECATED, use `from zenml import Model` instead."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """DEPRECATED, use `from zenml import Model` instead.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        logger.warning(
            "`ModelVersion` is deprecated. Please use `Model` instead."
        )
        super().__init__(*args, **kwargs)
