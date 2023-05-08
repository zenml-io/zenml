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


from pipelines import data_profiling_pipeline
from steps import (
    data_loader,
    data_splitter,
    test_data_profiler,
    train_data_profiler,
)

from zenml.logger import get_logger

logger = get_logger(__name__)


if __name__ == "__main__":

    pipeline_instance = data_profiling_pipeline(
        data_loader=data_loader(),
        data_splitter=data_splitter(),
        train_data_profiler=train_data_profiler,
        test_data_profiler=test_data_profiler,
    )

    pipeline_instance.run()
