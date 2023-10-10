#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

import sys
import time

from zenml import pipeline, step
from zenml.model.model_config import ModelConfig


@step
def _long_runner(run_time: int):
    time.sleep(run_time)
    return 1


def _multiprocessor(version, run_name, run_time):
    @pipeline(
        model_config=ModelConfig(
            name="step",
            version=version,
            create_new_model_version=True,
            delete_new_version_on_failure=False,
        ),
        enable_cache=False,
    )
    def _inner_pipeline(run_time):
        _long_runner(run_time)

    _inner_pipeline.with_options(run_name=run_name)(run_time)


if __name__ == "__main__":
    version = None if sys.argv[1] == "" else sys.argv[1]
    run_name = sys.argv[2]
    run_time = int(sys.argv[3])
    _multiprocessor(version, run_name, run_time)
