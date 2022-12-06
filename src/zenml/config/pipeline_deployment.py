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
"""Pipeline deployment."""
import json
from typing import Any, Dict, Optional, cast
from uuid import UUID

import yaml

import zenml
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.schedule import Schedule
from zenml.config.step_configurations import Step
from zenml.config.strict_base_model import StrictBaseModel


class PipelineDeployment(StrictBaseModel):
    """Class representing the deployment of a ZenML pipeline."""

    zenml_version: str = zenml.__version__
    run_name: str
    schedule: Optional[Schedule] = None
    stack_id: UUID
    pipeline: PipelineConfiguration
    pipeline_id: Optional[UUID] = None
    steps: Dict[str, Step] = {}

    def add_extra(self, key: str, value: Any) -> None:
        """Adds an extra key-value pair to the pipeline configuration.

        Args:
            key: Key for which to add the extra value.
            value: The extra value.
        """
        self.pipeline.extra[key] = value

    def yaml(self, **kwargs: Any) -> str:
        """Yaml representation of the deployment.

        Args:
            **kwargs: Kwargs to pass to the pydantic json(...) method.

        Returns:
            Yaml string representation of the deployment.
        """
        dict_ = json.loads(self.json(**kwargs, sort_keys=False))
        return cast(str, yaml.dump(dict_, sort_keys=False))
