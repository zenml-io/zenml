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

from zenml.pipelines import BasePipeline
from zenml.steps import step_interfaces


class TrainingPipeline(BasePipeline):
    """Class for the classic training pipeline implementation"""

    def connect(  # type: ignore[override]
        self,
        datasource: step_interfaces.BaseDatasourceStep,
        splitter: step_interfaces.BaseSplitStep,
        analyzer: step_interfaces.BaseAnalyzerStep,
        preprocessor: step_interfaces.BasePreprocessorStep,
        trainer: step_interfaces.BaseTrainerStep,
        evaluator: step_interfaces.BaseEvaluatorStep,
    ) -> None:
        """Main connect method for the standard training pipelines

        Args:
            datasource: the step responsible for the data ingestion
            splitter: the step responsible for splitting the dataset into
                train, test, val
            analyzer: the step responsible for extracting the statistics and
                the schema
            preprocessor: the step responsible for preprocessing the data
            trainer: the step responsible for training a model
            evaluator: the step responsible for computing the evaluation of
                the trained model
        """
        # Ingesting the datasource
        dataset = datasource()

        # Splitting the data
        train, test, validation = splitter(dataset=dataset)  # type:ignore

        # Analyzing the train dataset
        statistics, schema = analyzer(dataset=train)  # type:ignore

        # Preprocessing the splits
        train_t, test_t, validation_t = preprocessor(  # type:ignore
            train_dataset=train,
            test_dataset=test,
            validation_dataset=validation,
            statistics=statistics,
            schema=schema,
        )

        # Training the model
        model = trainer(train_dataset=train_t, validation_dataset=validation_t)

        # Evaluating the trained model
        evaluator(model=model, dataset=test_t)  # type:ignore
