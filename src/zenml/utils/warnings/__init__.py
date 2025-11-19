#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Initialization of the warning utils module.

The `warnings` module contains utilities that help centralize
and improve warning management.
"""

from zenml.utils.warnings.controller import WarningController
from zenml.utils.warnings.registry import WarningCodes

WARNING_CONTROLLER = WarningController.create()

__all__ = [
    "WARNING_CONTROLLER",
    "WarningCodes"
]
