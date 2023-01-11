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

"""Implementation of Deepchecks suite results materializer."""

import os
from typing import Any, Type, Union

from deepchecks.core.check_result import CheckResult
from deepchecks.core.suite import SuiteResult

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

RESULTS_FILENAME = "results.json"


class DeepchecksResultMaterializer(BaseMaterializer):
    """Materializer to read data to and from CheckResult and SuiteResult objects."""

    ASSOCIATED_TYPES = (
        CheckResult,
        SuiteResult,
    )
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA_ANALYSIS

    def load(self, data_type: Type[Any]) -> Union[CheckResult, SuiteResult]:
        """Reads a Deepchecks check or suite result from a serialized JSON file.

        Args:
            data_type: The type of the data to read.

        Returns:
            A Deepchecks CheckResult or SuiteResult.

        Raises:
            RuntimeError: if the input data type is not supported.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, RESULTS_FILENAME)

        json_res = io_utils.read_file_contents_as_string(filepath)
        if data_type == SuiteResult:
            res = SuiteResult.from_json(json_res)
        elif data_type == CheckResult:
            res = CheckResult.from_json(json_res)
        else:
            raise RuntimeError(f"Unknown data type: {data_type}")
        return res

    def save(self, result: Union[CheckResult, SuiteResult]) -> None:
        """Creates a JSON serialization for a CheckResult or SuiteResult.

        Args:
            result: A Deepchecks CheckResult or SuiteResult.
        """
        super().save(result)

        filepath = os.path.join(self.uri, RESULTS_FILENAME)

        serialized_json = result.to_json(True)
        io_utils.write_file_contents_as_string(filepath, serialized_json)
