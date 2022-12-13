#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the Great Expectations materializers."""

import os
from typing import Any, Dict, Type

from great_expectations.checkpoint.types.checkpoint_result import (  # type: ignore[import]
    CheckpointResult,
)
from great_expectations.core import ExpectationSuite  # type: ignore[import]
from great_expectations.core.expectation_validation_result import (  # type: ignore[import]
    ExpectationSuiteValidationResult,
)
from great_expectations.data_context.types.base import (  # type: ignore[import]
    CheckpointConfig,
)
from great_expectations.data_context.types.resource_identifiers import (  # type: ignore[import]
    ValidationResultIdentifier,
)
from great_expectations.types import SerializableDictDot  # type: ignore[import]

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import yaml_utils
from zenml.utils.source_utils import import_class_by_path

ARTIFACT_FILENAME = "artifact.json"


class GreatExpectationsMaterializer(BaseMaterializer):
    """Materializer to read/write Great Expectation objects."""

    ASSOCIATED_TYPES = (
        ExpectationSuite,
        CheckpointResult,
    )
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA_ANALYSIS

    @staticmethod
    def preprocess_checkpoint_result_dict(
        artifact_dict: Dict[str, Any]
    ) -> None:
        """Pre-processes a GE checkpoint dict before it is used to de-serialize a GE CheckpointResult object.

        The GE CheckpointResult object is not fully de-serializable
        due to some missing code in the GE codebase. We need to compensate
        for this by manually converting some of the attributes to
        their correct data types.

        Args:
            artifact_dict: A dict containing the GE checkpoint result.
        """

        def preprocess_run_result(key: str, value: Any) -> Any:
            if key == "validation_result":
                return ExpectationSuiteValidationResult(**value)
            return value

        artifact_dict["checkpoint_config"] = CheckpointConfig(
            **artifact_dict["checkpoint_config"]
        )
        validation_dict = {}
        for result_ident, results in artifact_dict["run_results"].items():
            validation_ident = (
                ValidationResultIdentifier.from_fixed_length_tuple(
                    result_ident.split("::")[1].split("/")
                )
            )
            validation_results = {
                result_name: preprocess_run_result(result_name, result)
                for result_name, result in results.items()
            }
            validation_dict[validation_ident] = validation_results
        artifact_dict["run_results"] = validation_dict

    def load(self, data_type: Type[Any]) -> SerializableDictDot:
        """Reads and returns a Great Expectations object.

        Args:
            data_type: The type of the data to read.

        Returns:
            A loaded Great Expectations object.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, ARTIFACT_FILENAME)
        artifact_dict = yaml_utils.read_json(filepath)
        data_type = import_class_by_path(artifact_dict.pop("data_type"))

        if data_type is CheckpointResult:
            self.preprocess_checkpoint_result_dict(artifact_dict)

        return data_type(**artifact_dict)

    def save(self, obj: SerializableDictDot) -> None:
        """Writes a Great Expectations object.

        Args:
            obj: A Great Expectations object.
        """
        super().save(obj)
        filepath = os.path.join(self.uri, ARTIFACT_FILENAME)
        artifact_dict = obj.to_json_dict()
        artifact_type = type(obj)
        artifact_dict[
            "data_type"
        ] = f"{artifact_type.__module__}.{artifact_type.__name__}"
        yaml_utils.write_json(filepath, artifact_dict)
