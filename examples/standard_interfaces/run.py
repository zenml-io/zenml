#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
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
import os

from zenml.integrations.sklearn import steps as sklearn_steps
from zenml.integrations.tensorflow import steps as tf_steps
from zenml.pipelines.builtin_pipelines import TrainingPipeline
from zenml.steps import builtin_steps

# Configuring the datasource
datasource = builtin_steps.PandasDatasource(
    builtin_steps.PandasDatasourceConfig(path=os.getenv("test_data"))
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
preprocesser = sklearn_steps.SklearnStandardScaler(
    sklearn_steps.SklearnStandardScalerConfig(ignore_columns=["has_diabetes"])
)

# Configuring the training step
trainer = tf_steps.TensorflowBinaryClassifier(
    tf_steps.TensorflowBinaryClassifierConfig(target_column="has_diabetes")
)

# Configuring the evaluation step
evaluator = sklearn_steps.SklearnEvaluator(
    sklearn_steps.SklearnEvaluatorConfig(label_class_column="has_diabetes")
)

# Create the pipeline and run it
pipeline_instance = TrainingPipeline(
    datasource=datasource,
    splitter=splitter,
    analyzer=analyzer,
    preprocesser=preprocesser,
    trainer=trainer,
    evaluator=evaluator,
    enable_cache=False,
)
pipeline_instance.run()
