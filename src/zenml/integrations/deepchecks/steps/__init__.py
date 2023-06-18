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
"""Initialization of the Deepchecks Standard Steps."""

from zenml.integrations.deepchecks.steps.deepchecks_data_drift import (
    deepchecks_data_drift_check_step,
)
from zenml.integrations.deepchecks.steps.deepchecks_data_integrity import (
    deepchecks_data_integrity_check_step,
)
from zenml.integrations.deepchecks.steps.deepchecks_model_drift import (
    deepchecks_model_drift_check_step,
)
from zenml.integrations.deepchecks.steps.deepchecks_model_validation import (
    deepchecks_model_validation_check_step,
)
