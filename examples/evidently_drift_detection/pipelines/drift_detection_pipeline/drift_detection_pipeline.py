#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from zenml.integrations.constants import EVIDENTLY, SKLEARN
from zenml.pipelines import pipeline


@pipeline(enable_cache=False, required_integrations=[EVIDENTLY, SKLEARN])
def drift_detection_pipeline(
    data_loader,
    data_splitter,
    drift_detector,
    drift_analyzer,
):
    """Links all the steps together in a pipeline"""
    data = data_loader()
    reference_dataset, comparison_dataset = data_splitter(data)
    drift_report, _ = drift_detector(
        reference_dataset=reference_dataset,
        comparison_dataset=comparison_dataset,
    )
    drift_analyzer(drift_report)
