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

from typing import Dict, Text, Any, Type

from tfx.dsl.components.base import executor_spec
from tfx.components.evaluator.component import Evaluator
from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen
from tfx.components.trainer.component import Trainer
from tfx.components.transform.component import Transform
from tfx.extensions.google_cloud_ai_platform.trainer import \
    executor as ai_platform_trainer_executor
from tfx.orchestration import pipeline
from tfx.proto import trainer_pb2

import zenml.core.pipelines.config.standard_config as exp_keys
from zenml.core.backends.orchestrator.orchestrator_local_backend import \
    OrchestratorLocalBackend
from zenml.core.backends.processing.processing_local_backend import \
    ProcessingLocalBackend
from zenml.core.backends.training.training_local_backend import \
    TrainingLocalBackend
from zenml.core.components.session_transform.sequence_transform import \
    SequenceTransform
from zenml.core.components.split_gen.component import SplitGen
from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.steps.deployer import DeployerStep
from zenml.core.steps.evaluator import EvaluatorStep
from zenml.core.steps.preprocesser import PreprocesserStep
from zenml.core.steps.split.base_split_step import BaseSplitStep
from zenml.core.steps.timeseries import TimeseriesStep
from zenml.core.steps.trainer import TrainerStep
from zenml.utils.constants import PREPROCESSING_FN, TRAINER_FN
from zenml.utils.enums import GDPComponent
from zenml.utils.enums import TrainingTypes, ServingTypes
from zenml.utils.post_training_utils import view_statistics, get_schema_proto


def sanitize_name_for_ai_platform(name: str):
    """
    Args:
        name (str):
    """
    return 'ce_' + name.replace('-', '_').lower()


class TrainingPipeline(BasePipeline):
    """Training Pipeline definition to

    TrainingPipeline is a general-purpose training pipeline for most ML
    training runs. One pipeline runs one experiment on a datasource.
    """

    def add_datasource(self, datasource: Type[BaseDatasource]):
        """
        Add datasource to pipeline.

        Args:
            datasource: class of type BaseDatasource
        """
        if datasource.has_run():
            # add it as a step
            self.steps_dict['data'] = datasource.DATA_STEP
        else:
            # do something else?
            pass

    def add_split(self, split_step: Type[BaseSplitStep]):
        self.steps_dict['split'] = split_step

    def add_timeseries(self, timeseries_step: TimeseriesStep):
        self.steps_dict['timeseries'] = timeseries_step

    def add_preprocesser(self, preprocessor_step: PreprocesserStep):
        self.steps_dict['preprocessor'] = preprocessor_step

    def add_trainer(self, trainer_step: TrainerStep):
        self.steps_dict['trainer'] = trainer_step

    def add_evaluator(self, evaluator_step: EvaluatorStep):
        self.steps_dict['evaluator'] = evaluator_step

    def add_deployment(self, deployment_step: DeployerStep):
        self.steps_dict['deployment'] = deployment_step

    def view_statistics(self):
        """View statistics for training pipeline."""
        # TODO: [HIGH] Remove hard-coded pipeline name
        artifact_uris = self.repo.get_artifacts_uri_by_component(
            'penguin_local_no_tuning_4', 'StatisticsGen')
        view_statistics(artifact_uris[0])

    def view_schema(self):
        # TODO: [HIGH] Remove hard-coded pipeline name
        artifact_uris = self.repo.get_artifacts_uri_by_component(
            'penguin_local_no_tuning_4', 'SchemaGen')
        return get_schema_proto(artifact_uris[0])

    def get_tfx_pipeline(self, spec: Dict[Text, Any]) -> pipeline.Pipeline:
        """
        Args:
            spec:
        """
        #################
        # CONFIGURATION #
        #################
        exp_keys.GlobalKeys.key_check(experiment_args)

        component_list = []

        ############
        # RAW DATA #
        ############

        # Block to read the data from the corresponding BQ table
        splits = SplitGen(
            config=experiment_args,
            test_mode=spec['test_mode'],
            instance_name=GDPComponent.SplitGen.name)

        statistics_split = StatisticsGen(
            examples=splits.outputs.examples,
            instance_name=GDPComponent.SplitStatistics.name)

        schema_split = SchemaGen(
            statistics=statistics_split.outputs.output,
            infer_feature_shape=False,
            instance_name=GDPComponent.SplitSchema.name)

        datapoints = splits.outputs.examples
        schema = schema_split.outputs.schema

        component_list.extend([splits,
                               statistics_split,
                               schema_split])

        ###############
        # TIME-SERIES #
        ###############
        # Block to deal with sequential data
        if exp_keys.GlobalKeys.TIMESERIES_ in experiment_args:
            sequence_transform = SequenceTransform(
                examples=datapoints,
                schema=schema,
                config=experiment_args,
                instance_name=GDPComponent.SequenceTransform.name)

            statistics_sequence = StatisticsGen(
                examples=sequence_transform.outputs.output,
                instance_name=GDPComponent.SequenceStatistics.name)

            schema_sequence = SchemaGen(
                statistics=statistics_sequence.outputs.output,
                infer_feature_shape=True,
                instance_name=GDPComponent.SequenceSchema.name)

            datapoints = sequence_transform.outputs.output
            schema = schema_sequence.outputs.schema

            component_list.extend([sequence_transform,
                                   statistics_sequence,
                                   schema_sequence])

        #################
        # PREPROCESSING #
        #################
        transform = Transform(examples=datapoints,
                              schema=schema,
                              preprocessing_fn=PREPROCESSING_FN,
                              custom_config=experiment_args,
                              instance_name=GDPComponent.Transform.name)
        component_list.extend([transform])

        ############
        # TRAINING #
        ############
        trainer_kwargs = {'custom_config': experiment_args}
        if spec['training_type'] == TrainingTypes.gcaip.name:
            trainer_kwargs.update({
                'custom_executor_spec': executor_spec.ExecutorClassSpec(
                    ai_platform_trainer_executor.GenericExecutor)
            })
            from tfx.extensions.google_cloud_ai_platform.trainer.executor \
                import \
                TRAINING_ARGS_KEY, JOB_ID_KEY
            trainer_kwargs['custom_config'].update(
                {TRAINING_ARGS_KEY: spec[TRAINING_ARGS_KEY],
                 JOB_ID_KEY: sanitize_name_for_ai_platform(cloud_job_prefix)})

        trainer = Trainer(
            transformed_examples=transform.outputs.transformed_examples,
            transform_graph=transform.outputs.transform_graph,
            run_fn=TRAINER_FN,
            schema=schema,
            train_args=trainer_pb2.TrainArgs(),
            eval_args=trainer_pb2.EvalArgs(),
            instance_name=GDPComponent.Trainer.name,
            **trainer_kwargs)

        component_list.extend([trainer])

        #############
        # EVALUATOR #
        #############
        eval_config = build_eval_config(config=experiment_args)
        evaluator = Evaluator(
            examples=transform.outputs.transformed_examples,
            model_exports=trainer.outputs.model,
            eval_config=eval_config,
            instance_name=GDPComponent.Evaluator.name)
        component_list.append(evaluator)

        ###########
        # SERVING #
        ###########

        from tfx.components.pusher.component import Pusher
        from tfx.extensions.google_cloud_ai_platform.pusher import \
            executor as ai_platform_pusher_executor
        from tfx.proto import pusher_pb2

        from zenml.core.components.model_validator.component import \
            ModelValidator

        # model validator
        model_validator = ModelValidator(
            examples=datapoints,
            model=trainer.outputs.model,
            instance_name=GDPComponent.ModelValidator.name,
        )
        component_list.append(model_validator)

        # pusher
        pusher_kwargs = {
            'model_export': trainer.outputs.output,
            'model_blessing': model_validator.outputs.blessing,
            'push_destination': pusher_pb2.PushDestination(
                filesystem=pusher_pb2.PushDestination.Filesystem(
                    base_directory=spec['serving_model_dir']))
        }

        if spec['serving_type'] == ServingTypes.gcaip.name:
            pusher_kwargs.update(
                {'custom_executor_spec': executor_spec.ExecutorClassSpec(
                    ai_platform_pusher_executor.Executor)})
        pusher_kwargs['custom_config'] = {
            'ai_platform_serving_args': spec['ai_platform_serving_args']
        }
        pusher_kwargs['instance_name'] = GDPComponent.Deployer.name

        pusher = Pusher(**pusher_kwargs)
        component_list.append(pusher)

        return pipeline.Pipeline(
            pipeline_name=spec['pipeline_name'],
            pipeline_root=spec['pipeline_root'],
            components=component_list,
            beam_pipeline_args=spec['execution_args'],
            enable_cache=spec['pipeline_enable_cache'],
            metadata_connection_config=spec['metadata_connection_config'],
            log_root=spec['pipeline_log_root'])

    def get_default_backends(self) -> Dict:
        """Gets list of default backends for this pipeline."""
        # For base class, orchestration is always necessary
        return {
            OrchestratorLocalBackend.BACKEND_KEY: OrchestratorLocalBackend(),
            ProcessingLocalBackend.BACKEND_KEY: ProcessingLocalBackend(),
            TrainingLocalBackend.BACKEND_KEY: TrainingLocalBackend(),
        }

    def is_completed(self) -> bool:
        mandatory_steps = ['split', 'preprocessor', 'trainer', 'evaluator',
                           'deployment']
        for step_name in mandatory_steps:
            if step_name not in self.steps_dict.keys():
                raise AssertionError(f'Mandatory step {step_name} not added.')
        return True
