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

# ----------------------------------------------------------------------------
# Copyright (C) 2021-2022 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#

"""
The logic of the `from_json` is contributed by the Deepchecks team and is copied
herein with full credit to them.
"""

import os
import tempfile
from typing import Any, Type

from deepchecks.core.suite import SuiteResult

from zenml.artifacts import DataAnalysisArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "results.json"


class DeepchecksResultMaterializer(BaseMaterializer):
    """Materializer to read data to and from SuiteResult objects."""

    ASSOCIATED_TYPES = (SuiteResult,)
    ASSOCIATED_ARTIFACT_TYPES = (DataAnalysisArtifact,)

    def handle_input(self, data_type: Type[Any]) -> SuiteResult:
        """Reads a deepchecks result from a serialized JSON file."""
        super().handle_input(data_type)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

        # Copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)

        # Make a temporary phantom artifact
        with open(temp_file, "r") as f:
            json_res = f.read()
            res = SuiteResult.from_json(json_res)

        # Cleanup and return
        fileio.rmtree(temp_dir)
        return res

    def handle_return(self, result: SuiteResult) -> None:
        """Creates a JSON serialization for a SuiteResult.

        Args:
            result: A deepchecks.SuiteResult.
        """
        super().handle_return(result)

        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)

        serialized_json = result.to_json(False)

        # Make a temporary phantom artifact
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=True
        ) as f:
            f.write(serialized_json)
            # Copy it into artifact store
            fileio.copy(f.name, filepath)
