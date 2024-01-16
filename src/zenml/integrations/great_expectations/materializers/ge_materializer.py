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
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type, Union, cast

from great_expectations.checkpoint.types.checkpoint_result import (  # type: ignore[import-untyped]
    CheckpointResult,
)
from great_expectations.core import (  # type: ignore[import-untyped]
    ExpectationSuite,
)
from great_expectations.core.expectation_validation_result import (  # type: ignore[import-untyped]
    ExpectationSuiteValidationResult,
)
from great_expectations.data_context.types.base import (  # type: ignore[import-untyped]
    CheckpointConfig,
)
from great_expectations.data_context.types.resource_identifiers import (  # type: ignore[import-untyped]
    ExpectationSuiteIdentifier,
    ValidationResultIdentifier,
)
from great_expectations.types import (  # type: ignore[import-untyped]
    SerializableDictDot,
)

from zenml.enums import ArtifactType, VisualizationType
from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import source_utils, yaml_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

ARTIFACT_FILENAME = "artifact.json"


class GreatExpectationsMaterializer(BaseMaterializer):
    """Materializer to read/write Great Expectation objects."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (
        ExpectationSuite,
        CheckpointResult,
    )
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[
        ArtifactType
    ] = ArtifactType.DATA_ANALYSIS

    @staticmethod
    def preprocess_checkpoint_result_dict(
        artifact_dict: Dict[str, Any],
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
        filepath = os.path.join(self.uri, ARTIFACT_FILENAME)
        artifact_dict = yaml_utils.read_json(filepath)
        data_type = source_utils.load(artifact_dict.pop("data_type"))

        if data_type is CheckpointResult:
            self.preprocess_checkpoint_result_dict(artifact_dict)

        return data_type(**artifact_dict)

    def save(self, obj: SerializableDictDot) -> None:
        """Writes a Great Expectations object.

        Args:
            obj: A Great Expectations object.
        """
        filepath = os.path.join(self.uri, ARTIFACT_FILENAME)
        artifact_dict = obj.to_json_dict()
        artifact_type = type(obj)
        artifact_dict[
            "data_type"
        ] = f"{artifact_type.__module__}.{artifact_type.__name__}"
        yaml_utils.write_json(filepath, artifact_dict)

    def save_visualizations(
        self, data: Union[ExpectationSuite, CheckpointResult]
    ) -> Dict[str, VisualizationType]:
        """Saves visualizations for the given Great Expectations object.

        Args:
            data: The Great Expectations object to save visualizations for.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        visualizations = {}

        if isinstance(data, CheckpointResult):
            result = cast(CheckpointResult, data)
            identifier = next(iter(result.run_results.keys()))
        else:
            suite = cast(ExpectationSuite, data)
            identifier = ExpectationSuiteIdentifier(
                suite.expectation_suite_name
            )

        context = GreatExpectationsDataValidator.get_data_context()
        sites = context.get_docs_sites_urls(identifier)
        for site in sites:
            url = site["site_url"]
            visualizations[url] = VisualizationType.HTML

        return visualizations

    def extract_metadata(
        self, data: Union[ExpectationSuite, CheckpointResult]
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given Great Expectations object.

        Args:
            data: The Great Expectations object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        if isinstance(data, CheckpointResult):
            return {
                "checkpoint_result_name": data.name,
                "checkpoint_result_passed": data.success,
            }
        elif isinstance(data, ExpectationSuite):
            return {
                "expectation_suite_name": data.name,
            }
        return {}
