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
from typing import Any, Dict, List, Optional

from pydantic.json import pydantic_encoder

from zenml.config.source import Source
from zenml.config.step_configurations import StepSpec
from zenml.config.strict_base_model import StrictBaseModel


class PipelineSpec(StrictBaseModel):
    """Specification of a pipeline."""

    # Versions:
    # - 0.2: Legacy BasePipeline in release <=0.39.1, the upstream steps and
    #   inputs in the step specs refer to the step names, not the pipeline
    #   parameter names
    # - 0.3: Legacy BasePipeline in release >0.39.1, the upstream steps and
    #   inputs in the step specs refer to the pipeline parameter names
    # - 0.4: New Pipeline class, the upstream steps and
    #   inputs in the step specs refer to the pipeline parameter names
    version: str = "0.4"
    source: Optional[Source] = None
    parameters: Dict[str, Any] = {}
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
        from packaging import version

        dict_ = self.dict()

        if self.source:
            dict_["source"] = self.source.import_path

        for step_dict in dict_["steps"]:
            step_dict["source"] = Source.parse_obj(
                step_dict["source"]
            ).import_path

        if version.parse(self.version) < version.parse("0.4"):
            # Keep backwards compatibility with old pipeline versions
            dict_.pop("source")
            dict_.pop("parameters")

        return json.dumps(dict_, sort_keys=False, default=pydantic_encoder)
