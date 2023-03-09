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
"""The hooks package exposes some standard hooks that can be used in ZenML.

Hooks are functions that run after a step has exited.
"""

from zenml.hooks.alerter_hooks import alerter_success_hook
from zenml.hooks.alerter_hooks import alerter_failure_hook
from zenml.hooks.hook_validators import resolve_and_validate_hook

__all__ = [
    "alerter_success_hook",
    "alerter_failure_hook",
    "resolve_and_validate_hook",
]
