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

from pydantic import Field

from zenml.config.frozen_base_model import FrozenBaseModel
from zenml.config.source import Source, SourceWithValidator
from zenml.config.step_configurations import StepSpec
from zenml.utils.json_utils import pydantic_encoder


class OutputSpec(FrozenBaseModel):
    """Pipeline output specification."""

    step_name: str
    output_name: str


class PipelineSpec(FrozenBaseModel):
    """Specification of a pipeline."""

    # Versions:
    # - 0.2: Legacy BasePipeline in release <=0.39.1, the upstream steps and
    #   inputs in the step specs refer to the step names, not the pipeline
    #   parameter names
    # - 0.3: Legacy BasePipeline in release >0.39.1, the upstream steps and
    #   inputs in the step specs refer to the pipeline parameter names
    # - 0.4: New Pipeline class, the upstream steps and
    #   inputs in the step specs refer to the pipeline parameter names
    # - 0.5: Adds outputs and output schema
    version: str = "0.5"
    source: Optional[SourceWithValidator] = None
    parameters: Dict[str, Any] = {}
    steps: List[StepSpec]
    outputs: List[OutputSpec] = []
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON schema of the pipeline outputs. This is only set "
        "for pipeline specs with version >= 0.5. If the value is None, the "
        "schema generation failed, which is most likely because some of the "
        "pipeline outputs are not JSON serializable.",
    )

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

        dict_ = self.model_dump()

        if self.source:
            dict_["source"] = self.source.import_path

        for step_dict in dict_["steps"]:
            step_dict["source"] = Source.model_validate(
                step_dict["source"]
            ).import_path

        if version.parse(self.version) < version.parse("0.4"):
            # Keep backwards compatibility with old pipeline versions
            dict_.pop("source")
            dict_.pop("parameters")

        return json.dumps(dict_, sort_keys=False, default=pydantic_encoder)
