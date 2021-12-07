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

from zenml.steps.builtin_steps import PandasDatasource, PandasDatasourceConfig
from zenml.steps.builtin_steps import PandasAnalyzer

from zenml.integrations.tensorflow.steps import TensorflowTrainer
from zenml.integrations.tensorflow.steps import TensorflowEvaluator

from zenml.integrations.sklearn.steps import SklearnSplitter, SklearnSplitterConfig
from zenml.integrations.sklearn.steps import SklearnPreprocesser

from zenml.pipelines.builtin_pipelines import TrainingPipeline

pipeline_instance = TrainingPipeline(
    datasource=PandasDatasource(
        config=PandasDatasourceConfig(path=os.getenv("test_data")),
        ),
    splitter=SklearnSplitter(
        config=SklearnSplitterConfig(ratios={"train": 0.7,
                                             "test": 0.15,
                                             "validation": 0.15})
    ),
    analyzer=PandasAnalyzer(),
    preprocesser=SklearnPreprocesser(),
    trainer=TensorflowTrainer(),
    evaluator=TensorflowEvaluator()
)
pipeline_instance.run()
