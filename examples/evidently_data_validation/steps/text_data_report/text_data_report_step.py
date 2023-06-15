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
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.integrations.evidently.steps import (
    EvidentlyColumnMapping,
    evidently_report_step,
)

text_data_report = evidently_report_step.with_options(
    parameters=dict(
        column_mapping=EvidentlyColumnMapping(
            target="Rating",
            numerical_features=["Age", "Positive_Feedback_Count"],
            categorical_features=[
                "Division_Name",
                "Department_Name",
                "Class_Name",
            ],
            text_features=["Review_Text", "Title"],
        ),
        metrics=[
            EvidentlyMetricConfig.metric("DataQualityPreset"),
            EvidentlyMetricConfig.metric(
                "TextOverviewPreset", column_name="Review_Text"
            ),
            EvidentlyMetricConfig.metric_generator(
                "ColumnRegExpMetric",
                columns=["Review_Text", "Title"],
                reg_exp=r"[A-Z][A-Za-z0-9 ]*",
            ),
        ],
        # We need to download the NLTK data for the TextOverviewPreset
        download_nltk_data=True,
    ),
)
