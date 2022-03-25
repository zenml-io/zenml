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
from urllib.request import urlopen

from zenml.integrations.constants import SKLEARN
from zenml.integrations.sklearn import steps as sklearn_steps
from zenml.logger import get_logger
from zenml.pipelines import BasePipeline
from zenml.repository import Repository
from zenml.steps import builtin_steps, step_interfaces

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


class Chapter2Pipeline(BasePipeline):
    """Class for Chapter 2 of the class-based API"""

    def connect(
        self,
        datasource: step_interfaces.BaseDatasourceStep,
        splitter: step_interfaces.BaseSplitStep,
        analyzer: step_interfaces.BaseAnalyzerStep,
        preprocessor: step_interfaces.BasePreprocessorStep,
    ) -> None:
        # Ingesting the datasource
        dataset = datasource()

        # Splitting the data
        train, test, validation = splitter(dataset=dataset)

        # Analyzing the train dataset
        statistics, schema = analyzer(dataset=train)

        # Preprocessing the splits
        train_t, test_t, validation_t = preprocessor(
            train_dataset=train,
            test_dataset=test,
            validation_dataset=validation,
            statistics=statistics,
            schema=schema,
        )


if __name__ == "__main__":

    # Create an instance of the pipeline and run it
    pipeline_instance = Chapter2Pipeline(
        required_integrations=[SKLEARN],
        datasource=builtin_steps.PandasDatasource(
            config=builtin_steps.PandasDatasourceConfig(path=DATASET_PATH)
        ),
        splitter=sklearn_steps.SklearnSplitter(
            config=sklearn_steps.SklearnSplitterConfig(
                ratios={"train": 0.7, "test": 0.15, "validation": 0.15}
            )
        ),
        analyzer=builtin_steps.PandasAnalyzer(
            config=builtin_steps.PandasAnalyzerConfig(
                percentiles=[0.2, 0.4, 0.6, 0.8, 1.0]
            )
        ),
        preprocessor=sklearn_steps.SklearnStandardScaler(
            config=sklearn_steps.SklearnStandardScalerConfig(
                ignore_columns=["has_diabetes"]
            )
        ),
    )

    pipeline_instance.run()

    # Post-execution
    repo = Repository()
    p = repo.get_pipeline(pipeline_name="Chapter2Pipeline")
    runs = p.runs
    print(f"Pipeline `Chapter2Pipeline` has {len(runs)} run(s)")
    run = runs[-1]
    print(f"The run you just made has {len(run.steps)} step(s).")
