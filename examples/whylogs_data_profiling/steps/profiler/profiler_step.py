#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from zenml.integrations.whylogs.steps import (
    WhylogsProfilerConfig,
    whylogs_profiler_step,
)

# A quick way of enhancing your pipeline with whylogs profiling features
# is with the `whylogs_profiler_step` function, which creates a step that runs
# whylogs data profiling on an input dataframe and returns the generated
# profile as an output artifact.

train_data_profiler = whylogs_profiler_step(
    step_name="train_data_profiler",
    config=WhylogsProfilerConfig(),
    dataset_id="model-2",
)
test_data_profiler = whylogs_profiler_step(
    step_name="test_data_profiler",
    config=WhylogsProfilerConfig(),
    dataset_id="model-3",
)
