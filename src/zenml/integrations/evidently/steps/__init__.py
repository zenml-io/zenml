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
"""Initialization of the Evidently Standard Steps."""

from zenml.integrations.evidently.column_mapping import EvidentlyColumnMapping
from zenml.integrations.evidently.steps.evidently_report import (
    EvidentlyReportParameters,
    EvidentlyReportStep,
    EvidentlySingleDatasetReportStep,
    evidently_report_step,
)
from zenml.integrations.evidently.steps.evidently_test import (
    EvidentlyTestParameters,
    EvidentlySingleDatasetTestStep,
    EvidentlyTestStep,
    evidently_test_step,
)
from zenml.integrations.evidently.steps.evidently_profile import (
    EvidentlyProfileParameters,
    EvidentlyProfileStep,
    evidently_profile_step,
)
