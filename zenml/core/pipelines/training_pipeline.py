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

import json
import os
from pathlib import Path
from typing import Dict, Text, Any, List

import tensorflow as tf
from tfx.components.evaluator.component import Evaluator
from tfx.components.pusher.component import Pusher
from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen
from tfx.components.trainer.component import Trainer
from tfx.components.transform.component import Transform
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
from zenml.core.standards import standard_keys as keys
from zenml.core.steps.deployer.gcaip_deployer import GCAIPDeployer
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.base_preprocesser import \
    BasePreprocesserStep
from zenml.core.steps.split.base_split_step import BaseSplit
from zenml.core.steps.trainer.base_trainer import BaseTrainerStep
from zenml.utils import constants
from zenml.utils import path_utils
from zenml.utils.enums import GDPComponent
from zenml.utils.logger import get_logger
from zenml.utils.post_training.post_training_utils import \
    evaluate_single_pipeline, view_statistics, view_schema, detect_anomalies
from zenml.utils.post_training.post_training_utils import \
    get_feature_spec_from_schema, convert_raw_dataset_to_pandas

logger = get_logger(__name__)


class TrainingPipeline(BasePipeline):
    """
    Definition of the Training Pipeline class.

    TrainingPipeline is a general-purpose training pipeline for most ML
    training runs. One pipeline runs one experiment on a single datasource.
    """

    PIPELINE_TYPE = 'training'

    def get_tfx_component_list(self, config: Dict[Text, Any]) -> List:
        """
        Builds the training pipeline as a series of TFX components.

        Args:
            config: A ZenML configuration in dictionary format.

        Returns:
            A chronological list of TFX components making up the training
             pipeline.

        """
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
        training_backend: TrainingLocalBackend = \
            self.backends_dict[TrainingLocalBackend.BACKEND_KEY]
        training_kwargs = {
            'custom_executor_spec': training_backend.get_executor_spec(),
            'custom_config': steps[keys.TrainingSteps.TRAINING]
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
        if keys.TrainingSteps.DEPLOYMENT in steps:
            serving_args = steps[keys.TrainingSteps.DEPLOYMENT]['args']

            project_id = serving_args['project_id']
            output_base_dir = self.artifact_store.path
            if 'model_name' in serving_args:
                model_name = serving_args['model_name']
            else:
                model_name = self.pipeline_name().replace('-', '_')

            gcaip_deployer = GCAIPDeployer(output_base_dir=output_base_dir,
                                           project_id=project_id,
                                           model_name=model_name)

            pusher_config = gcaip_deployer.build_pusher_config()
            pusher_executor_spec = gcaip_deployer.get_executor_spec()

            pusher = Pusher(model_export=trainer.outputs.output,
                            custom_executor_spec=pusher_executor_spec,
                            **pusher_config).with_id(
                GDPComponent.Deployer.name)

            component_list.append(pusher)

        return component_list

    def add_split(self, split_step: BaseSplit):
        self.steps_dict[keys.TrainingSteps.SPLIT] = split_step

    def add_preprocesser(self, preprocessor_step: BasePreprocesserStep):
        self.steps_dict[keys.TrainingSteps.PREPROCESSING] = preprocessor_step

    def add_trainer(self, trainer_step: BaseTrainerStep):
        self.steps_dict[keys.TrainingSteps.TRAINING] = trainer_step

    def add_evaluator(self, evaluator_step: TFMAEvaluator):
        self.steps_dict[keys.TrainingSteps.EVALUATION] = evaluator_step

    def add_deployment(self, deployment_step: GCAIPDeployer):
        self.steps_dict[keys.TrainingSteps.DEPLOYMENT] = deployment_step

    def view_statistics(self, magic: bool = False):
        """
        View statistics for training pipeline in HTML.

        Args:
            magic (bool): Creates HTML page if False, else
            creates a notebook cell.
        """
        logger.info(
            'Viewing statistics. If magic=False then a new window will open '
            'up with a notebook for evaluation. If magic=True, then an '
            'attempt will be made to append to the current notebook.')
        uri = self.get_artifacts_uri_by_component(
            GDPComponent.SplitStatistics.name)[0]
        view_statistics(uri, magic)

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        uri = self.get_artifacts_uri_by_component(
            GDPComponent.SplitSchema.name)[0]
        view_schema(uri)

    def evaluate(self, magic: bool = False):
        """
        Evaluate pipeline from the evaluator steps artifacts.

        Args:
            magic: Creates new window if False, else creates notebook cells.
        """
        from zenml.utils.enums import PipelineStatusTypes
        if self.get_status() != PipelineStatusTypes.Succeeded.name:
            logger.info(
                "Cannot evaluate a pipeline that has not executed "
                "successfully. Please run the pipeline and ensure it "
                "completes successfully to evaluate it.")
            return
        if keys.TrainingSteps.EVALUATION not in self.steps_dict:
            logger.info("This pipeline does not contain an evaluation step.")
            return

        logger.info(
            'Evaluating pipeline. If magic=False then a new window will open '
            'up with a notebook for evaluation. If magic=True, then an '
            'attempt will be made to append to the current notebook.')
        return evaluate_single_pipeline(self, magic=magic)

    def download_model(self, out_path: Text = None, overwrite: bool = False):
        """Download model to out_path"""
        # TODO: [LOW] Implement when Deployer logic figured out
        raise NotImplementedError('Not implemented!')
        # model_path = self.get_artifacts_uri_by_component(
        #     GDPComponent.Deployer.name)
        # if out_path:
        #     from zenml.utils.path_utils import move
        #     move(model_path, out_path, overwrite)
        # else:
        #     out_path = model_path
        # logger.debug(f'Model: {out_path}')

    def view_anomalies(self, split_name='eval'):
        """
        View schema of data flowing in pipeline.

        Args:
            split_name: name of split to detect anomalies on
        """
        stats_uri = self.get_artifacts_uri_by_component(
            GDPComponent.SplitStatistics.name)
        schema_uri = self.get_artifacts_uri_by_component(
            GDPComponent.SplitSchema.name)[0]
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

    def get_hyperparameters(self) -> Dict:
        """
        Gets all hyperparameters of pipeline
        """
        # TODO: [LOW] Check if this is necessary
        if not self.is_executed_in_metadata_store:
            raise Exception('This pipeline has not been run yet.')

        executions = self.metadata_store.get_pipeline_executions(self)

        hparams = {}
        for e in executions:
            component_id = e.properties['component_id'].string_value
            if component_id == GDPComponent.Trainer.name:
                custom_config = json.loads(
                    e.properties['custom_config'].string_value)
                fn = custom_config[keys.StepKeys.SOURCE]
                params = custom_config[keys.StepKeys.ARGS]
                # filter out None values to not break compare tool
                params = {k: v for k, v in params.items() if v is not None}
                hparams[f'{component_id}_fn'] = fn
                hparams.update(params)
        return hparams

    def sample_transformed_data(self,
                                split_name: Text = 'eval',
                                sample_size: int = 100000):
        """
        Samples transformed data as a pandas DataFrame.

        Args:
            split_name: name of split to see
            sample_size: # of rows to sample.
        """
        base_uri = self.get_artifacts_uri_by_component(
            GDPComponent.Transform.name)[0]
        transform_schema = os.path.join(base_uri, 'transformed_metadata')
        spec = get_feature_spec_from_schema(transform_schema)

        base_uri = Path(base_uri)
        id_ = base_uri.name
        transform_data_path = os.path.join(
            str(base_uri.parent.parent), 'transformed_examples', id_)

        split_data_path = os.path.join(transform_data_path, split_name)
        data_files = path_utils.list_dir(split_data_path)
        dataset = tf.data.TFRecordDataset(data_files, compression_type='GZIP')
        return convert_raw_dataset_to_pandas(dataset, spec, sample_size)
