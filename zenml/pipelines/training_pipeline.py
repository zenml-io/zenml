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
from tfx.components.common_nodes.importer_node import ImporterNode
from tfx.components.pusher.component import Pusher
from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen
from tfx.components.transform.component import Transform
from tfx.types import standard_artifacts

from zenml import constants
from zenml.backends.training import TrainingBaseBackend
from zenml.components import Sequencer, SplitGen, Trainer, Evaluator
from zenml.enums import GDPComponent
from zenml.exceptions import DoesNotExistException, \
    PipelineNotSucceededException
from zenml.logger import get_logger
from zenml.pipelines import BasePipeline
from zenml.standards import standard_keys as keys
from zenml.steps.deployer import BaseDeployerStep
from zenml.steps.evaluator import BaseEvaluatorStep
from zenml.steps.preprocesser import BasePreprocesserStep
from zenml.steps.preprocesser.base_preprocesser import build_split_mapping
from zenml.steps.sequencer import BaseSequencerStep
from zenml.steps.split import BaseSplitStep
from zenml.steps.trainer import BaseTrainerStep
from zenml.utils import path_utils
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

        schema_data = ImporterNode(
            instance_name=GDPComponent.DataSchema.name,
            source_uri=data_pipeline.get_artifacts_uri_by_component(
                GDPComponent.DataSchema.name)[0],
            artifact_type=standard_artifacts.Schema)

        statistics_data = ImporterNode(
            instance_name=GDPComponent.DataStatistics.name,
            source_uri=data_pipeline.get_artifacts_uri_by_component(
                GDPComponent.DataStatistics.name)[0],
            artifact_type=standard_artifacts.ExampleStatistics)

        component_list.extend([data, schema_data, statistics_data])

        datapoints = data.outputs.result

        #############
        # SPLITTING #
        #############
        # Block to read the data from the corresponding BQ table
        split_config = steps[keys.TrainingSteps.SPLIT]
        splits = SplitGen(
            input_examples=datapoints,
            source=split_config[keys.StepKeys.SOURCE],
            source_args=split_config[keys.StepKeys.ARGS],
            schema=schema_data.outputs.result,
            statistics=statistics_data.outputs.result,
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

        ##############
        # SEQUENCING #
        ##############
        if keys.TrainingSteps.SEQUENCER in steps:
            sequencer_config = steps[keys.TrainingSteps.SEQUENCER]
            sequencer = Sequencer(
                input_examples=datapoints,
                schema=schema,
                statistics=statistics_split.outputs.statistics,
                source=sequencer_config[keys.StepKeys.SOURCE],
                source_args=sequencer_config[keys.StepKeys.ARGS]
            ).with_id(GDPComponent.Sequencer.name)

            sequencer_statistics = StatisticsGen(
                examples=sequencer.outputs.output_examples
            ).with_id(GDPComponent.SequencerStatistics.name)

            sequencer_schema = SchemaGen(
                statistics=sequencer_statistics.outputs.output,
                infer_feature_shape=True,
            ).with_id(GDPComponent.SequencerSchema.name)

            datapoints = sequencer.outputs.output_examples
            schema = sequencer_schema.outputs.schema

            component_list.extend([sequencer,
                                   sequencer_statistics,
                                   sequencer_schema])

        #################
        # PREPROCESSING #
        #################
        split_mapping = build_split_mapping(
            steps[keys.TrainingSteps.PREPROCESSER][keys.StepKeys.ARGS])

        transform = Transform(
            preprocessing_fn=constants.PREPROCESSING_FN,
            examples=datapoints,
            schema=schema,
            splits_config=split_mapping,
            custom_config=steps[keys.TrainingSteps.PREPROCESSER]
        ).with_id(GDPComponent.Transform.name)

        component_list.extend([transform])

        ############
        # TRAINING #
        ############
        training_backend: TrainingBaseBackend = \
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
            **training_kwargs
        ).with_id(GDPComponent.Trainer.name)

        component_list.extend([trainer])

        #############
        # EVALUATOR #
        #############
        if keys.TrainingSteps.EVALUATOR in steps:
            evaluator_config = steps[keys.TrainingSteps.EVALUATOR]
            # TODO [MEDIUM]: This check should ideally not happen here,
            #  integrate it into the component
            eval_source = evaluator_config['source'].split('@')[0]
            if eval_source == \
                    'zenml.steps.evaluator.agnostic_evaluator' \
                    '.AgnosticEvaluator':
                evaluator = Evaluator(
                    source=evaluator_config[keys.StepKeys.SOURCE],
                    source_args=evaluator_config[keys.StepKeys.ARGS],
                    examples=trainer.outputs.test_results,
                ).with_id(GDPComponent.Evaluator.name)
            elif eval_source == \
                    'zenml.steps.evaluator.tfma_evaluator.TFMAEvaluator':
                evaluator = Evaluator(
                    source=evaluator_config[keys.StepKeys.SOURCE],
                    source_args=evaluator_config[keys.StepKeys.ARGS],
                    examples=transform.outputs.transformed_examples,
                    model=trainer.outputs.model,
                ).with_id(GDPComponent.Evaluator.name)
            else:
                raise ValueError(
                    'Please use either the built-in TFMAEvaluator '
                    'or the AgnosticEvaluator')
            component_list.append(evaluator)

        ###########
        # SERVING #
        ###########
        if keys.TrainingSteps.DEPLOYER in steps:
            deployer: BaseDeployerStep = \
                self.steps_dict[keys.TrainingSteps.DEPLOYER]
            pusher_config = deployer._build_pusher_args()
            pusher_executor_spec = deployer._get_executor_spec()
            pusher = Pusher(model_export=trainer.outputs.model,
                            custom_executor_spec=pusher_executor_spec,
                            **pusher_config).with_id(
                GDPComponent.Deployer.name)

            component_list.append(pusher)

        return component_list

    def add_split(self, split_step: BaseSplitStep):
        self.steps_dict[keys.TrainingSteps.SPLIT] = split_step

    def add_sequencer(self, sequencer_step: BaseSequencerStep):
        self.steps_dict[keys.TrainingSteps.SEQUENCER] = sequencer_step

    def add_preprocesser(self, preprocessor_step: BasePreprocesserStep):
        self.steps_dict[keys.TrainingSteps.PREPROCESSER] = preprocessor_step

    def add_trainer(self, trainer_step: BaseTrainerStep):
        self.steps_dict[keys.TrainingSteps.TRAINER] = trainer_step

    def add_evaluator(self, evaluator_step: BaseEvaluatorStep):
        self.steps_dict[keys.TrainingSteps.EVALUATOR] = evaluator_step

    def add_deployment(self, deployment_step: BaseDeployerStep):
        self.steps_dict[keys.TrainingSteps.DEPLOYER] = deployment_step

    def view_statistics(self, magic: bool = False, port: int = 0):
        """
        View statistics for training pipeline in HTML.

        Args:
            magic (bool): Creates HTML page if False, else
            creates a notebook cell.
            port (int): Port at which to launch the statistics facet.
        """
        logger.info(
            'Viewing statistics. If magic=False then a new window will open '
            'up with a notebook for evaluation. If magic=True, then an '
            'attempt will be made to append to the current notebook.')
        uri = self.get_artifacts_uri_by_component(
            GDPComponent.SplitStatistics.name)[0]
        view_statistics(uri, magic, port)

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        uri = self.get_artifacts_uri_by_component(
            GDPComponent.SplitSchema.name)[0]
        view_schema(uri)

    def evaluate(self, magic: bool = False, port: int = 0):
        """
        Evaluate pipeline from the evaluator and trainer steps artifact.

        Args:
            magic: Creates new window if False, else creates notebook cells.
            port: At which port to deploy jupyter notebook.
        """
        from zenml.enums import PipelineStatusTypes
        if self.get_status() != PipelineStatusTypes.Succeeded.name:
            logger.info(
                "Cannot evaluate a pipeline that has not executed "
                "successfully. Please run the pipeline and ensure it "
                "completes successfully to evaluate it.")
            raise PipelineNotSucceededException(name=self.name)
        if keys.TrainingSteps.EVALUATOR not in self.steps_dict:
            logger.info("This pipeline does not contain an Evaluator step.")
            raise DoesNotExistException(
                name=f'{keys.TrainingSteps.EVALUATOR}',
                reason='This pipeline does not contain an Evaluator step!')
        if keys.TrainingSteps.TRAINER not in self.steps_dict:
            logger.info("This pipeline does not contain a TRAINER step.")
            raise DoesNotExistException(
                name=f'{keys.TrainingSteps.TRAINER}',
                reason='This pipeline does not contain a Trainer step!')

        logger.info(
            'Evaluating pipeline. If magic=False then a new window will open '
            'up with a notebook for evaluation. If magic=True, then an '
            'attempt will be made to append to the current notebook.')
        return evaluate_single_pipeline(self, magic=magic, port=port)

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
            GDPComponent.SplitStatistics.name)[0]
        schema_uri = self.get_artifacts_uri_by_component(
            GDPComponent.SplitSchema.name)[0]
        detect_anomalies(stats_uri, schema_uri, split_name)

    def steps_completed(self) -> bool:
        mandatory_steps = [keys.TrainingSteps.SPLIT,
                           keys.TrainingSteps.PREPROCESSER,
                           keys.TrainingSteps.TRAINER]
        for step_name in mandatory_steps:
            if step_name not in self.steps_dict.keys():
                raise AssertionError(f'Mandatory step {step_name} not added.')
        return True

    def get_model_uri(self):
        """Gets model artifact."""
        uris = self.get_artifacts_uri_by_component(
            GDPComponent.Trainer.name, False)
        return uris[0]

    def get_hyperparameters(self) -> Dict:
        """
        Gets all hyper-parameters of pipeline.
        """
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
