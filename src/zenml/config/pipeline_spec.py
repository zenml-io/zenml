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
"""Pipeline configuration classes."""
import json
from typing import Any, List

from zenml.config.source import Source
from zenml.config.step_configurations import StepSpec
from zenml.config.strict_base_model import StrictBaseModel


class PipelineSpec(StrictBaseModel):
    """Specification of a pipeline."""

    version: str = "0.2"
    steps: List[StepSpec]

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same pipeline.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is referring to the same pipeline.
        """
        if isinstance(other, PipelineSpec):
            return self.steps == other.steps
        return NotImplemented

    @property
    def json_with_string_sources(self) -> str:
        """JSON representation with sources replaced by their import path.

        Returns:
            The JSON representation.
        """
        dict_ = self.dict()

        for step_dict in dict_["steps"]:
            step_dict["source"] = Source.parse_obj(
                step_dict["source"]
            ).import_path

        return json.dumps(dict_, sort_keys=False)
