#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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
"""Training pipeline step to create a pipeline that trains on data."""

import os
from typing import Dict, Text, Any, List

from tfx.components.evaluator.component import Evaluator
from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen
from tfx.components.trainer.component import Trainer
from tfx.components.transform.component import Transform
from tfx.dsl.components.base import executor_spec
from tfx.extensions.google_cloud_ai_platform.trainer import \
    executor as ai_platform_trainer_executor
from tfx.proto import trainer_pb2

from zenml.core.backends.orchestrator.local.orchestrator_local_backend import \
    OrchestratorLocalBackend
from zenml.core.backends.processing.processing_local_backend import \
    ProcessingLocalBackend
from zenml.core.backends.training.training_local_backend import \
    TrainingLocalBackend
from zenml.core.components.data_gen.component import DataGen
from zenml.core.components.split_gen.component import SplitGen
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.pipelines.utils import sanitize_name_for_ai_platform
from zenml.core.standards import standard_keys as keys
from zenml.core.steps.deployer.base_deployer import BaseDeployerStep
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.base_preprocesser import \
    BasePreprocesserStep
from zenml.core.steps.split.base_split_step import BaseSplitStep
from zenml.core.steps.trainer.base_trainer import BaseTrainerStep
from zenml.utils import constants
from zenml.utils.enums import GDPComponent
from zenml.utils.logger import get_logger
from zenml.utils.post_training.post_training_utils import \
    get_statistics_artifact, \
    get_schema_artifact, get_pusher_artifact, \
    evaluate_single_pipeline, view_statistics, view_schema, detect_anomalies

logger = get_logger(__name__)


class TrainingPipeline(BasePipeline):
    """Training Pipeline definition to

    TrainingPipeline is a general-purpose training pipeline for most ML
    training runs. One pipeline runs one experiment on a datasource.
    """
    PIPELINE_TYPE = 'training'

    def get_tfx_component_list(self, config: Dict[Text, Any]) -> List:
        specs = self.get_pipeline_spec(config)
        steps = config[keys.GlobalKeys.STEPS]

        component_list = []

        ############
        # RAW DATA #
        ############
        data_config = steps[keys.TrainingSteps.DATA]
        data = DataGen(
            source=data_config[keys.StepKeys.SOURCE],
            source_args=data_config[keys.StepKeys.ARGS]
        ).with_id(GDPComponent.DataGen.name)

        statistics_data = StatisticsGen(
            examples=data.outputs.examples
        ).with_id(GDPComponent.DataStatistics.name)

        schema_data = SchemaGen(
            statistics=statistics_data.outputs.output,
            infer_feature_shape=True,
        ).with_id(GDPComponent.DataSchema.name)

        component_list.extend([data,
                               statistics_data,
                               schema_data])

        datapoints = data.outputs.examples

        #################
        #   SPLITTING   #
        #################
        # Block to read the data from the corresponding BQ table
        split_config = steps[keys.TrainingSteps.SPLIT]
        splits = SplitGen(
            input_examples=datapoints,
            source=split_config[keys.StepKeys.SOURCE],
            source_args=split_config[keys.StepKeys.ARGS],
            schema=schema_data.outputs.schema,
            statistics=statistics_data.outputs.output,
        ).with_id(GDPComponent.SplitGen.name)

        datapoints = splits.outputs.examples

        statistics_split = StatisticsGen(
            examples=datapoints
        ).with_id(GDPComponent.SplitStatistics.name)

        schema_split = SchemaGen(
            statistics=statistics_split.outputs.output,
            infer_feature_shape=False,
        ).with_id(GDPComponent.SplitSchema.name)

        schema = schema_split.outputs.schema

        component_list.extend([splits,
                               statistics_split,
                               schema_split])

        #################
        # PREPROCESSING #
        #################
        transform = Transform(
            preprocessing_fn=constants.PREPROCESSING_FN,
            examples=datapoints,
            schema=schema,
            custom_config=steps[keys.TrainingSteps.PREPROCESSING]
        ).with_id(GDPComponent.Transform.name)

        component_list.extend([transform])

        ############
        # TRAINING #
        ############
        # TODO: [LOW] Hard-coded
        training_type = specs['training_args']['type']
        training_args = specs['training_args']['args']

        kwargs = {'custom_config': steps[keys.TrainingSteps.TRAINING]}

        if training_type == 'gcaip':
            kwargs.update({
                'custom_executor_spec': executor_spec.ExecutorClassSpec(
                    ai_platform_trainer_executor.GenericExecutor)})

            # TODO: [LOW] Fix the constant issue
            cloud_job_prefix = 'some_constant'

            from tfx.extensions.google_cloud_ai_platform.trainer.executor \
                import TRAINING_ARGS_KEY, JOB_ID_KEY
            kwargs['custom_config'].update(
                {TRAINING_ARGS_KEY: training_args,
                 JOB_ID_KEY: sanitize_name_for_ai_platform(cloud_job_prefix)})

        from tfx.components.trainer.executor import GenericExecutor
        Trainer.EXECUTOR_SPEC = executor_spec.ExecutorClassSpec(
            GenericExecutor)

        trainer = Trainer(
            transformed_examples=transform.outputs.transformed_examples,
            transform_graph=transform.outputs.transform_graph,
            run_fn=constants.TRAINER_FN,
            schema=schema,
            train_args=trainer_pb2.TrainArgs(),
            eval_args=trainer_pb2.EvalArgs(),
            **kwargs
        ).with_id(GDPComponent.Trainer.name)

        component_list.extend([trainer])

        #############
        # EVALUATOR #
        #############
        if keys.TrainingSteps.EVALUATION in steps:
            from zenml.utils import source_utils
            eval_module = '.'.join(
                constants.EVALUATOR_MODULE_FN.split('.')[:-1])
            eval_module_file = constants.EVALUATOR_MODULE_FN.split('.')[-1]
            abs_path = source_utils.get_absolute_path_from_module(eval_module)
            custom_extractor_path = os.path.join(abs_path,
                                                 eval_module_file) + '.py'
            eval_step: TFMAEvaluator = TFMAEvaluator.from_config(
                steps[keys.TrainingSteps.EVALUATION])
            eval_config = eval_step.build_eval_config()
            evaluator = Evaluator(
                examples=transform.outputs.transformed_examples,
                model=trainer.outputs.model,
                eval_config=eval_config,
                module_file=custom_extractor_path,
            ).with_id(GDPComponent.Evaluator.name)
            component_list.append(evaluator)

        ###########
        # SERVING #
        ###########

        # from tfx.components.pusher.component import Pusher
        # from tfx.extensions.google_cloud_ai_platform.pusher import \
        #     executor as ai_platform_pusher_executor
        # from tfx.proto import pusher_pb2
        #
        # # pusher
        # pusher_kwargs = {
        #     'model_export': trainer.outputs.output,
        #     'push_destination': pusher_pb2.PushDestination(
        #         filesystem=pusher_pb2.PushDestination.Filesystem(
        #             base_directory=spec['serving_model_dir']))
        # }
        #
        # if spec['serving_type'] == ServingTypes.gcaip.name:
        #     pusher_kwargs.update(
        #         {'custom_executor_spec': executor_spec.ExecutorClassSpec(
        #             ai_platform_pusher_executor.Executor)})
        # pusher_kwargs['custom_config'] = {
        #     'ai_platform_serving_args': spec['ai_platform_serving_args']
        # }
        # pusher_kwargs['instance_name'] = GDPComponent.Deployer.name
        #
        # pusher = Pusher(**pusher_kwargs)
        # component_list.append(pusher)

        return component_list

    def add_split(self, split_step: BaseSplitStep):
        self.steps_dict[keys.TrainingSteps.SPLIT] = split_step

    def add_preprocesser(self, preprocessor_step: BasePreprocesserStep):
        self.steps_dict[keys.TrainingSteps.PREPROCESSING] = preprocessor_step

    def add_trainer(self, trainer_step: BaseTrainerStep):
        self.steps_dict[keys.TrainingSteps.TRAINING] = trainer_step

    def add_evaluator(self, evaluator_step: TFMAEvaluator):
        self.steps_dict[keys.TrainingSteps.EVALUATION] = evaluator_step

    def add_deployment(self, deployment_step: BaseDeployerStep):
        self.steps_dict[keys.TrainingSteps.DEPLOYMENT] = deployment_step

    def view_statistics(self, magic: bool = False):
        """
        View statistics for training pipeline in HTML.

        Args:
            magic (bool): Creates HTML page if False, else
            creates a notebook cell.
        """
        uri = get_statistics_artifact(
            self.pipeline_name, GDPComponent.SplitStatistics.name)
        view_statistics(uri, magic)

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        uri = get_schema_artifact(
            self.pipeline_name, GDPComponent.SplitSchema.name)
        view_schema(uri)

    def evaluate(self):
        """Evaluate pipeline."""
        return evaluate_single_pipeline(self.pipeline_name)

    def download_model(self, out_path: Text = None, overwrite: bool = False):
        """Download model to out_path"""
        model_path = get_pusher_artifact(self.pipeline_name)
        if out_path:
            from zenml.utils.path_utils import move
            move(model_path, out_path, overwrite)
        else:
            out_path = model_path
        logger.debug(f'Model: {out_path}')

    def view_anomalies(self, split_name='eval'):
        """
        View schema of data flowing in pipeline.

        Args:
            split_name: name of split to detect anomalies on
        """
        stats_uri = get_statistics_artifact(
            self.pipeline_name, GDPComponent.SplitStatistics.name)
        schema_uri = get_schema_artifact(
            self.pipeline_name, GDPComponent.SplitSchema.name)
        detect_anomalies(stats_uri, schema_uri, split_name)

    def get_default_backends(self) -> Dict:
        """Gets list of default backends for this pipeline."""
        # For base class, orchestration is always necessary
        return {
            OrchestratorLocalBackend.BACKEND_KEY: OrchestratorLocalBackend(),
            ProcessingLocalBackend.BACKEND_KEY: ProcessingLocalBackend(),
            TrainingLocalBackend.BACKEND_KEY: TrainingLocalBackend(),
        }

    def steps_completed(self) -> bool:
        mandatory_steps = [keys.TrainingSteps.SPLIT,
                           keys.TrainingSteps.PREPROCESSING,
                           keys.TrainingSteps.TRAINING,
                           keys.TrainingSteps.DATA]
        for step_name in mandatory_steps:
            if step_name not in self.steps_dict.keys():
                raise AssertionError(f'Mandatory step {step_name} not added.')
        return True
