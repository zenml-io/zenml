#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from typing import Annotated

import pandas as pd

from zenml import step
from zenml.integrations.evidently.column_mapping import EvidentlyColumnMapping
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.integrations.evidently.steps import evidently_report_step


@step
def drift_build_report(
    dataset_trn: pd.DataFrame, dataset_inf: pd.DataFrame
) -> Annotated[str, "report"]:
    report, _ = evidently_report_step(
        reference_dataset=dataset_trn.drop(columns=["target"]),
        comparison_dataset=dataset_inf,
        column_mapping=EvidentlyColumnMapping(
            numerical_features=list(dataset_inf.columns)
        ),
        metrics=[
            EvidentlyMetricConfig.metric("DataQualityPreset"),
        ],
    )

    return report
