#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Execution overrides."""

from typing import Dict, Set

from zenml.config.frozen_base_model import FrozenBaseModel
from zenml.config.step_configurations import InputSourceOverride


class ExecutionOverrides(FrozenBaseModel):
    """Execution overrides applied to every run of a snapshot."""

    steps_to_skip: Set[str] = set()
    skip_successful_steps: bool = False
    input_overrides: Dict[str, Dict[str, InputSourceOverride]] = {}
    default_input_overrides: Dict[str, Dict[str, InputSourceOverride]] = {}

    def get_input_overrides(
        self,
        invocation_id: str,
        step_name: str,
        include_step_defaults: bool = True,
    ) -> Dict[str, InputSourceOverride]:
        """Input source overrides for an invocation.

        Args:
            invocation_id: The invocation ID of the step.
            step_name: The name of the step.
            include_step_defaults: Whether to include the step-wide default
                overrides.

        Returns:
            The input source overrides for the invocation.
        """
        overrides: Dict[str, InputSourceOverride] = {}
        if include_step_defaults:
            overrides.update(self.default_input_overrides.get(step_name, {}))
        overrides.update(self.input_overrides.get(invocation_id, {}))
        return overrides
