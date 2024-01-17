# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import json

from zenml import step


@step
def drift_quality_gate(report: str, na_drift_tolerance: float = 0.1) -> None:
    """Analyze the Evidently Report and raise RuntimeError on
    high deviation of NA count in 2 datasets.

    Args:
        report: generated Evidently JSON report.
        na_drift_tolerance: If number of NAs in current changed more than threshold
            percentage error will be raised.

    Raises:
        RuntimeError: significant drift in NA Count
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    result = json.loads(report)["metrics"][0]["result"]
    if result["reference"]["number_of_missing_values"] > 0 and (
        abs(
            result["reference"]["number_of_missing_values"]
            - result["current"]["number_of_missing_values"]
        )
        / result["reference"]["number_of_missing_values"]
        > na_drift_tolerance
    ):
        raise RuntimeError(
            "Number of NA values in scoring dataset is significantly different compared to train dataset."
        )
    ### YOUR CODE ENDS HERE ###
