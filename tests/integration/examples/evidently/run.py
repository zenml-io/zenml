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

# from pipelines.text_report_test_pipeline.text_report_test import (
#     text_data_report_test_pipeline,
# )
#
# if __name__ == "__main__":
#     text_data_report_test_pipeline()
#
#     last_run = text_data_report_test_pipeline.model.last_run
#     text_analysis_step = last_run.steps["text_analyzer"]
#
#     print(
#         "Reference missing values: ",
#         text_analysis_step.outputs["ref_missing_values"].load(),
#     )
#     print(
#         "Comparison missing values: ",
#         text_analysis_step.outputs["comp_missing_values"].load(),
#     )
