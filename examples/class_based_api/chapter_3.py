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

from zenml.integrations.constants import SKLEARN, TENSORFLOW
from zenml.integrations.sklearn import steps as sklearn_steps
from zenml.integrations.tensorflow import steps as tf_steps
from zenml.logger import get_logger
from zenml.pipelines.builtin_pipelines import TrainingPipeline
from zenml.repository import Repository
from zenml.steps import builtin_steps

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


# Configuring the datasource
datasource = builtin_steps.PandasDatasource(
    builtin_steps.PandasDatasourceConfig(path=DATASET_PATH)
)

# Configuring the split step
splitter = sklearn_steps.SklearnSplitter(
    sklearn_steps.SklearnSplitterConfig(
        ratios={"train": 0.7, "test": 0.15, "validation": 0.15}
    )
)

# Configuring the analyzer step
analyzer = builtin_steps.PandasAnalyzer(
    builtin_steps.PandasAnalyzerConfig(percentiles=[0.2, 0.4, 0.6, 0.8, 1.0])
)

# Configuring the preprocessing step
preprocessor = sklearn_steps.SklearnStandardScaler(
    sklearn_steps.SklearnStandardScalerConfig(ignore_columns=["has_diabetes"])
)

# Configuring the training step
trainer = tf_steps.TensorflowBinaryClassifier(
    tf_steps.TensorflowBinaryClassifierConfig(
        target_column="has_diabetes", epochs=10
    )
)

# Configuring the evaluation step
evaluator = sklearn_steps.SklearnEvaluator(
    sklearn_steps.SklearnEvaluatorConfig(label_class_column="has_diabetes")
)


if __name__ == "__main__":

    # Create the pipeline and run it
    pipeline_instance = TrainingPipeline(
        required_integrations=[SKLEARN, TENSORFLOW],
        datasource=datasource,
        splitter=splitter,
        analyzer=analyzer,
        preprocessor=preprocessor,
        trainer=trainer,
        evaluator=evaluator,
    )
    pipeline_instance.run()

    # Post-execution
    repo = Repository()
    p = repo.get_pipeline(pipeline_name="TrainingPipeline")
    runs = p.runs
    print(f"Pipeline `TrainingPipeline` has {len(runs)} run(s)")
    run = runs[-1]
    print(f"The run you just made has {len(run.steps)} step(s).")
