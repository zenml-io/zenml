#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import SKLEARN, WHYLOGS

docker_settings = DockerSettings(required_integrations=[SKLEARN, WHYLOGS])


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def data_profiling_pipeline(
    data_loader,
    data_splitter,
    train_data_profiler,
    test_data_profiler,
):
    """Links all the steps together in a pipeline."""
    data, _ = data_loader()
    train, test = data_splitter(data)
    train_data_profiler(train)
    test_data_profiler(test)
