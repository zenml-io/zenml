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
from zenml.config import DockerSettings
from zenml.integrations.constants import SKLEARN
from zenml.pipelines import pipeline

docker_settings = DockerSettings(
    required_integrations=[SKLEARN],
    requirements=["pyarrow"],
)


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def text_data_report_test_pipeline(
    data_loader,
    data_splitter,
    text_report,
    text_test,
    text_analyzer,
):
    """Links all the steps together in a pipeline."""
    data = data_loader()
    reference_dataset, comparison_dataset = data_splitter(data)
    report, _ = text_report(
        reference_dataset=reference_dataset,
        comparison_dataset=comparison_dataset,
    )
    test_report, _ = text_test(
        reference_dataset=reference_dataset,
        comparison_dataset=comparison_dataset,
    )
    text_analyzer(report)
