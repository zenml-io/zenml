#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import io
import os
import tempfile
from typing import Any, List, Type

import jsonpickle
import jsonpickle.ext.pandas as jsonpickle_pd
import pandas as pd
import plotly
from deepchecks.core import SuiteResult
from deepchecks.core.check_result import CheckFailure, CheckResult
from deepchecks.core.condition import (
    Condition,
    ConditionCategory,
    ConditionResult,
)

from zenml.artifacts import DataAnalysisArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "results.json"

# registers jsonpickle pandas extension for pandas support in the to_json function
jsonpickle_pd.register_handlers()

__all__ = [
    "CheckJson",
    "CheckJsonFailure",
]


class CheckJson(CheckResult):
    """Class which returns from a check with result that can later be used for automatic pipelines and display value.
    Class containing the result of a check
    The class stores the results and display of the check. Evaluating the result in an IPython console / notebook
    will show the result display output.
    Parameters
    ----------
    json_data : str
        Json data
    """

    def __init__(self, json_data: str):
        json_dict = jsonpickle.loads(json_data)

        self.value = json_dict.get("value")
        self._check_name = json_dict.get("name")
        self.header = json_dict.get("header")
        self.params = json_dict.get("params")
        self.summary = json_dict.get("summary")

        conditions_table = json_dict.get("conditions_table")
        if conditions_table is not None:
            self.conditions_results = []
            conditions_table = jsonpickle.loads(conditions_table)
            for condition in conditions_table:
                cond_res = ConditionResult(
                    ConditionCategory[condition["Status"]],
                    condition["More Info"],
                )
                cond_res.set_name(condition["Condition"])
                self.conditions_results.append(cond_res)
        else:
            self.conditions_results = None
        json_display = json_dict.get("display")
        self.display = []
        if json_display is not None:
            for display_type, value in json_display:
                if display_type == "html":
                    self.display.append(value)
                elif display_type == "dataframe":
                    df: pd.DataFrame = pd.read_json(value, orient="records")
                    self.display.append(df)
                elif display_type == "plotly":
                    plotly_json = io.StringIO(value)
                    self.display.append(plotly.io.read_json(plotly_json))
                elif display_type == "plt":
                    self.display.append(
                        (f"<img src='data:image/png;base64,{value}'>")
                    )
                else:
                    raise ValueError(
                        f"Unexpected type of display received: {display_type}"
                    )

    def _get_metadata(self, _: bool = False):
        header = self.get_header()
        return {
            "name": self.check_name,
            "params": self.params,
            "header": header,
            "summary": self.summary,
        }

    def get_header(self) -> str:
        """Return header for display. if header was defined return it, else extract name of check class."""
        return self.header

    def process_conditions(self) -> List[Condition]:
        """Conditions are already processed it is to prevent errors."""

    @property
    def check_name(self):
        return self._check_name


class CheckJsonFailure(CheckFailure):
    """Class which holds a check run exception.
    Parameters
    ----------
    check : BaseCheck
    exception : Exception
    header_suffix : str , default ``
    """

    def __init__(self, json_data: str):
        json_dict = jsonpickle.loads(json_data)
        self.exception = json_dict.get("exception")
        self._check_name = json_dict.get("name")
        self.header = json_dict.get("header")
        self.params = json_dict.get("params")
        self.summary = json_dict.get("summary")

    def _get_metadata(self, _: bool = False):
        CheckJson._get_metadata()

    def __repr__(self):
        """Return string representation."""
        return self.header + ": " + str(self.exception)

    def print_traceback(self):
        """Print the traceback of the failure."""
        print(self.exception)

    @property
    def check_name(self):
        return self._check_name


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
            json_dict = jsonpickle.loads(json_res)
            name = json_dict["name"]
            results = []
            for res in json_dict["results"]:
                if jsonpickle.loads(res).get("exception"):
                    results.append(CheckJsonFailure(res))
                else:
                    results.append(CheckJson(res))
            res = SuiteResult(name, results)

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
