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
import os

from pipelines import spark_pipeline
from steps import (
    ImporterParameters,
    SplitParameters,
    importer_step,
    split_step,
    statistics_step,
    trainer_step,
    transformer_step,
)

if __name__ == "__main__":
    pipeline = spark_pipeline(
        importer=importer_step(
            params=ImporterParameters(path=os.getenv("SPARK_DEMO_DATASET"))
        ),
        analyzer=statistics_step(),
        splitter=split_step(
            params=SplitParameters(
                train_ratio=0.7,
                test_ratio=0.2,
                eval_ratio=0.1,
            ),
        ),
        processor=transformer_step(),
        trainer=trainer_step(),
    )
    pipeline.run()
