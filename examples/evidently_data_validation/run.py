#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from pipelines.text_report_test_pipeline.text_report_test import (
    text_data_report_test_pipeline,
)
from steps.data_loader.data_loader_step import data_loader
from steps.data_splitter.data_splitter_step import data_splitter
from steps.text_data_analyzer.text_analyzer_step import text_analyzer
from steps.text_data_report.text_data_report_step import text_data_report
from steps.text_data_test.text_data_test_step import text_data_test

from zenml.integrations.evidently.visualizers import EvidentlyVisualizer
from zenml.post_execution import get_pipeline


def visualize_statistics():
    """Visualize statistics from the last run of the pipeline."""
    pipeline = get_pipeline(pipeline="text_data_report_test_pipeline")
    text_report_step = pipeline.runs[0].get_step(step="text_report")
    EvidentlyVisualizer().visualize(text_report_step)
    text_test_step = pipeline.runs[0].get_step(step="text_test")
    EvidentlyVisualizer().visualize(text_test_step)


if __name__ == "__main__":
    pipeline_instance = text_data_report_test_pipeline(
        data_loader=data_loader(),
        data_splitter=data_splitter(),
        text_report=text_data_report,
        text_test=text_data_test,
        text_analyzer=text_analyzer(),
    )
    pipeline_instance.run()

    last_run = pipeline_instance.get_runs()[0]
    text_analysis_step = last_run.get_step(step="text_analyzer")

    print(
        "Reference missing values: ",
        text_analysis_step.outputs["ref_missing_values"].read(),
    )
    print(
        "Comparison missing values: ",
        text_analysis_step.outputs["comp_missing_values"].read(),
    )

    visualize_statistics()
