#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from typing import List, Optional, Union
from urllib.request import urlopen

import pandas as pd

from zenml.logger import get_logger
from zenml.pipelines import BasePipeline
from zenml.repository import Repository
from zenml.steps.step_interfaces.base_datasource_step import (
    BaseDatasourceConfig,
    BaseDatasourceStep,
)

logger = get_logger(__name__)

DATASET_PATH = "diabetes.csv"
DATASET_SRC = (
    "https://storage.googleapis.com/zenml-public-bucket/"
    "pima-indians-diabetes/diabetes.csv"
)

# Download the dataset for this example
if not os.path.isfile(DATASET_PATH):
    logger.info(f"Downloading dataset {DATASET_PATH}")
    with urlopen(DATASET_SRC) as data:
        content = data.read().decode()
    with open(DATASET_PATH, "w") as output:
        output.write(content)


class PandasDatasourceConfig(BaseDatasourceConfig):
    path: str
    sep: str = ","
    header: Union[int, List[int], str] = "infer"
    names: Optional[List[str]] = None
    index_col: Optional[Union[int, str, List[Union[int, str]], bool]] = None


class PandasDatasource(BaseDatasourceStep):
    def entrypoint(
        self,
        config: PandasDatasourceConfig,
    ) -> pd.DataFrame:
        return pd.read_csv(
            filepath_or_buffer=config.path,
            sep=config.sep,
            header=config.header,
            names=config.names,
            index_col=config.index_col,
        )


class Chapter1Pipeline(BasePipeline):
    """Class for Chapter 1 of the class-based API"""

    def connect(
        self,
        datasource: BaseDatasourceStep,
    ) -> None:
        datasource()


if __name__ == "__main__":

    pipeline_instance = Chapter1Pipeline(
        datasource=PandasDatasource(PandasDatasourceConfig(path=DATASET_PATH))
    )

    pipeline_instance.run()

    # Post-execution
    repo = Repository()
    p = repo.get_pipeline(pipeline_name="Chapter1Pipeline")
    runs = p.runs
    print(f"Pipeline `Chapter1Pipeline` has {len(runs)} run(s)")
    run = runs[-1]
    print(f"The run you just made has {len(run.steps)} step(s).")
    step = run.get_step("datasource")
    print(f"That step has {len(step.outputs)} output artifacts.")
