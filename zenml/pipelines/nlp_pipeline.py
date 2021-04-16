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

import os
from typing import Dict, Text, Any, List
from typing import Optional, Union

import tensorflow as tf
from tfx.components.common_nodes.importer_node import ImporterNode
from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen
from tfx.components.trainer.component import Trainer
from tfx.proto import trainer_pb2
from tfx.types import standard_artifacts

from zenml import constants
from zenml.backends.training import TrainingBaseBackend
from zenml.components import SplitGen, Trainer
from zenml.components import Tokenizer
from zenml.enums import GDPComponent
from zenml.enums import PipelineStatusTypes
from zenml.logger import get_logger
from zenml.pipelines import BasePipeline
from zenml.standards import standard_keys as keys
from zenml.steps.split import BaseSplitStep
from zenml.steps.tokenizer import BaseTokenizer
from zenml.steps.trainer import BaseTrainerStep

logger = get_logger(__name__)


class NLPPipeline(BasePipeline):
    PIPELINE_TYPE = "nlp"

    def predict_sentence(self, sequence: Union[Text, List[Text]]):
        """Call operator for local inference method"""

        if not self.get_status() == PipelineStatusTypes.Succeeded.name:
            print("Please run the pipeline first before running inference!")
            return

        trainer_step = self.steps_dict[keys.NLPSteps.TRAINER]

        # e.g. HuggingFace has special APIs for model loading,
        # so we fall back to a trainer step class method
        model_uri = os.path.join(self.get_model_uri(), "serving_model_dir")
        model = trainer_step.load_model(model_uri)

        tokenizer_step = self.steps_dict[keys.NLPSteps.TOKENIZER]

        tokenizer_step.load_vocab(self.get_tokenizer_uri())

        encoded = tokenizer_step.encode(sequence=sequence,
                                        output_format="tf_tensors")

        transformed_bert_features = {k: tf.reshape(v, (1, -1)) for k, v in
                                     encoded.items()}

        prediction = model(input_ids=transformed_bert_features, training=False)

        formatted = [
            {"label": model.config.id2label[item.argmax()],
             "score": item.max().item()}
            for item in tf.math.sigmoid(prediction.logits).numpy()
        ]

        print(formatted)

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
        # if there are no commits, then lets make one
        if self.datasource.is_empty:
            logger.info(
                f'Datasource {self.datasource.name} has no commits. Creating '
                f'the first one..')
            self.datasource_commit_id = self.datasource.commit()

        data_pipeline = self.datasource.get_data_pipeline_from_commit(
            self.datasource_commit_id)

        data = ImporterNode(
            instance_name=GDPComponent.DataGen.name,
            source_uri=data_pipeline.get_artifacts_uri_by_component(
                GDPComponent.DataGen.name)[0],
            artifact_type=standard_artifacts.Examples)
        component_list.extend([data])

        #############
        # TOKENIZER #
        #############
        tokenizer_config = steps[keys.NLPSteps.TOKENIZER]
        tokenizer = Tokenizer(
            source=tokenizer_config[keys.StepKeys.SOURCE],
            source_args=tokenizer_config[keys.StepKeys.ARGS],
            examples=data.outputs.result,
        ).with_id(GDPComponent.Tokenizer.name)

        component_list.extend([tokenizer])

        # return component_list

        statistics_data = StatisticsGen(
            examples=tokenizer.outputs.output_examples
        ).with_id(GDPComponent.DataStatistics.name)

        schema_data = SchemaGen(
            statistics=statistics_data.outputs.output,
            infer_feature_shape=True,
        ).with_id(GDPComponent.DataSchema.name)

        split_config = steps[keys.NLPSteps.SPLIT]
        splits = SplitGen(
            input_examples=tokenizer.outputs.output_examples,
            source=split_config[keys.StepKeys.SOURCE],
            source_args=split_config[keys.StepKeys.ARGS],
            schema=schema_data.outputs.schema,
            statistics=statistics_data.outputs.output,
        ).with_id(GDPComponent.SplitGen.name)

        component_list.extend([data,
                               statistics_data,
                               schema_data,
                               splits])

        ############
        # TRAINING #
        ############
        training_backend: Optional[TrainingBaseBackend] = \
            self.steps_dict[keys.NLPSteps.TRAINER].backend

        # default to local
        if training_backend is None:
            training_backend = TrainingBaseBackend()

        training_kwargs = {
            'custom_executor_spec': training_backend.get_executor_spec(),
            'custom_config': steps[keys.NLPSteps.TRAINER]
        }
        training_kwargs['custom_config'].update(
            training_backend.get_custom_config())

        trainer = Trainer(
            examples=splits.outputs.examples,
            run_fn=constants.TRAINER_FN,
            schema=schema_data.outputs.schema,
            train_args=trainer_pb2.TrainArgs(),
            eval_args=trainer_pb2.EvalArgs(),
            **training_kwargs
        ).with_id(GDPComponent.Trainer.name)

        component_list.extend([trainer])

        return component_list

    def steps_completed(self) -> bool:
        mandatory_steps = [keys.NLPSteps.DATA,
                           keys.NLPSteps.TOKENIZER,
                           keys.NLPSteps.SPLIT,
                           keys.NLPSteps.TRAINER,
                           ]

        for step_name in mandatory_steps:
            if step_name not in self.steps_dict.keys():
                raise AssertionError(f'Mandatory step {step_name} not added.')
        return True

    def add_tokenizer(self, tokenizer_step: BaseTokenizer):
        self.steps_dict[keys.NLPSteps.TOKENIZER] = tokenizer_step

    def add_split(self, split_step: BaseSplitStep):
        self.steps_dict[keys.NLPSteps.SPLIT] = split_step

    def add_trainer(self, trainer_step: BaseTrainerStep):
        self.steps_dict[keys.NLPSteps.TRAINER] = trainer_step

    def get_model_uri(self):
        """Gets model artifact."""
        uris = self.get_artifacts_uri_by_component(
            GDPComponent.Trainer.name, False)
        return uris[0]

    def get_schema_uri(self):
        """Gets transform artifact."""
        uris = self.get_artifacts_uri_by_component(
            GDPComponent.DataSchema.name, False)
        return uris[0]

    def get_tokenizer_uri(self):
        """Gets transform artifact."""
        uris = self.get_artifacts_uri_by_component(
            GDPComponent.Tokenizer.name, False)
        return uris[0]
