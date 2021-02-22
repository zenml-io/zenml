#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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
"""ZenML NLP Pipeline Prototype."""

from typing import Dict, Text, Any, List, Optional

from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen
from zenml.core.components.data_gen.component import DataGen
from zenml.core.components.split_gen.component import SplitGen
from tfx.components.transform.component import Transform
from tfx.components.trainer.component import Trainer
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.standards import standard_keys as keys
from zenml.utils.enums import GDPComponent
from zenml.core.backends.training.training_base_backend import \
    TrainingBaseBackend
from tfx.proto import trainer_pb2
from zenml.utils import constants

from zenml.core.steps.preprocesser.base_preprocesser import \
    BasePreprocesserStep
from zenml.core.steps.trainer.base_trainer import BaseTrainerStep
from zenml.core.steps.split.base_split_step import BaseSplit

TOKENIZER = "tokenizer"


class NLPPipeline(BasePipeline):

    PIPELINE_TYPE = "nlp"

    def get_tfx_component_list(self, config: Dict[Text, Any]) -> List:
        """
        Builds the NLP pipeline as a series of TFX components.

        Args:
            config: A ZenML configuration in dictionary format.

        Returns:
            A chronological list of TFX components making up the NLP
             pipeline.

        """
        steps = config[keys.GlobalKeys.PIPELINE][keys.PipelineKeys.STEPS]

        component_list = []

        ############
        # RAW DATA #
        ############
        data_config = steps[keys.TrainingSteps.DATA]
        data = DataGen(
            name=self.datasource.name,
            source=data_config[keys.StepKeys.SOURCE],
            source_args=data_config[keys.StepKeys.ARGS]
        ).with_id(GDPComponent.DataGen.name)

        datapoints = data.outputs.examples

        statistics_data = StatisticsGen(
            examples=data.outputs.examples
        ).with_id(GDPComponent.DataStatistics.name)

        schema_data = SchemaGen(
            statistics=statistics_data.outputs.output,
        ).with_id(GDPComponent.DataSchema.name)

        split_config = steps[keys.TrainingSteps.SPLIT]
        splits = SplitGen(
            input_examples=datapoints,
            source=split_config[keys.StepKeys.SOURCE],
            source_args=split_config[keys.StepKeys.ARGS],
            schema=schema_data.outputs.schema,
            statistics=statistics_data.outputs.output,
        ).with_id(GDPComponent.SplitGen.name)

        examples = splits.outputs.examples

        component_list.extend([data,
                               statistics_data,
                               schema_data,
                               splits])

        schema = schema_data.outputs.schema

        #############
        # TOKENIZER #
        #############
        tokenizer_backend: Optional[TrainingBaseBackend] = \
            self.steps_dict[TOKENIZER].backend

        # default to local
        if tokenizer_backend is None:
            tokenizer_backend = TrainingBaseBackend()

        tokenizer_kwargs = {
            'custom_executor_spec': tokenizer_backend.get_executor_spec(),
            'custom_config': steps[TOKENIZER]
        }
        tokenizer_kwargs['custom_config'].update(
            tokenizer_backend.get_custom_config())

        tokenizer = Trainer(
            examples=examples,
            run_fn=constants.TRAINER_FN,
            schema=schema,
            train_args=trainer_pb2.TrainArgs(),
            eval_args=trainer_pb2.EvalArgs(),
            **tokenizer_kwargs
        ).with_id(TOKENIZER)

        component_list.extend([tokenizer])

        return component_list

        #################
        # PREPROCESSING #
        #################
        transform = Transform(
            preprocessing_fn=constants.PREPROCESSING_FN,
            examples=datapoints,
            schema=schema,
            custom_config=steps[keys.TrainingSteps.PREPROCESSER]
        ).with_id(GDPComponent.Transform.name)

        # component_list.extend([transform])

        ############
        # TRAINING #
        ############
        training_backend: Optional[TrainingBaseBackend] = \
            self.steps_dict[keys.TrainingSteps.TRAINER].backend

        # default to local
        if training_backend is None:
            training_backend = TrainingBaseBackend()

        training_kwargs = {
            'custom_executor_spec': training_backend.get_executor_spec(),
            'custom_config': steps[keys.TrainingSteps.TRAINER]
        }
        training_kwargs['custom_config'].update(
            training_backend.get_custom_config())

        trainer = Trainer(
            transformed_examples=transform.outputs.transformed_examples,
            transform_graph=transform.outputs.transform_graph,
            run_fn=constants.TRAINER_FN,
            schema=schema,
            train_args=trainer_pb2.TrainArgs(),
            eval_args=trainer_pb2.EvalArgs(),
            **training_kwargs
        ).with_id(GDPComponent.Trainer.name)

        # component_list.extend([trainer])

        return component_list

    def steps_completed(self) -> bool:
        mandatory_steps = [TOKENIZER,
                           # keys.TrainingSteps.PREPROCESSER,
                           # keys.TrainingSteps.TRAINER,
                           keys.TrainingSteps.DATA]

        for step_name in mandatory_steps:
            if step_name not in self.steps_dict.keys():
                raise AssertionError(f'Mandatory step {step_name} not added.')
        return True

    def add_tokenizer(self, tokenizer_step: Any):
        self.steps_dict[TOKENIZER] = tokenizer_step

    def add_split(self, split_step: BaseSplit):
        self.steps_dict[keys.TrainingSteps.SPLIT] = split_step

    def add_preprocesser(self, preprocessor_step: BasePreprocesserStep):
        self.steps_dict[keys.TrainingSteps.PREPROCESSER] = preprocessor_step

    def add_trainer(self, trainer_step: BaseTrainerStep):
        self.steps_dict[keys.TrainingSteps.TRAINER] = trainer_step
