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
"""Here lies the logic of running the pipeline. It consumes the input as
configuration"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import time
import uuid
from typing import Dict, Union
from typing import Text

import yaml


class PipelineRunner:
    """PipelineRunner runs (TFX) pipelines with appropriate backends.

    All backends need to get plugged in this class.
    """
    def __init__(self):
        pass

    def run(self, environment_yaml: Union[Text, Dict],
            experiment_yaml: Union[Text, Dict]):
        # Create the required gzipped tar file
        prepare_sdist()

        if isinstance(environment_yaml, Text) \
                and isinstance(experiment_yaml, Text):
            # Read both config files
            environment_dict = yaml.load(open(environment_yaml))
            experiment_dict = yaml.load(open(experiment_yaml))
        elif isinstance(environment_yaml, Dict) \
                and isinstance(experiment_yaml, Dict):
            environment_dict = environment_yaml
            experiment_dict = experiment_yaml
        else:
            raise AssertionError(
                'Params have to either both dict or both paths.')

        # Create a dict which includes the environment settings of the pipeline
        env_spec = get_pipeline_spec(environment_dict)
        # Create a proper JSON file for the experiment config
        config = create_experiment_json(experiment_dict, env_spec)
        str_config = json.dumps(config)

        # Create and execute the pipeline
        created_pipeline = create_normal_pipeline(
            env_spec,
            experiment_args=experiment_dict,
            cloud_job_prefix=str(time.time())
        )

        orchestrator = env_spec['orchestrator']

        if orchestrator == 'kubeflow':

            from tfx.orchestration.kubeflow import kubeflow_dag_runner
            from tfx.orchestration.kubeflow.kubeflow_dag_runner import \
                KubeflowDagRunner
            from gdp.utils.environment_utils import add_ce_env

            pipeline_operator_funcs = \
                kubeflow_dag_runner.get_default_pipeline_operator_funcs()
            pipeline_operator_funcs.append(
                add_ce_env(ZENML_PIPELINE_CONFIG, str_config))

            runner_config = kubeflow_dag_runner.KubeflowDagRunnerConfig(
                kubeflow_metadata_config=env_spec[
                    'metadata_connection_config'],
                tfx_image=GDP_IMAGE,
                pipeline_operator_funcs=pipeline_operator_funcs,
            )
            runner = KubeflowDagRunner(config=runner_config)
            runner._pipeline_id = str(uuid.uuid4())

            def pipeline_func():
                runner._construct_pipeline_graph(created_pipeline,
                                                 env_spec['pipeline_root'])

            # import kfp
            # from datetime import datetime
            # kfp_client = kfp.Client(
            #     host='https://kf-dev-04.endpoints.core-engine.cloud.goog
            #     /pipeline',
            #     client_id='973445798975-1brrhd1bmalcggu7v6aro8ttohmlpj8l.apps
            #     .googleusercontent.com',
            #     namespace='hamza',
            # )
            # test = kfp_client.create_run_from_pipeline_func(
            #     pipeline_func=pipeline_func,
            #     arguments={},
            #     run_name='remote_{}'.format(str(datetime.now())),
            #     experiment_name='maiot-version-upgrade-0214',
            # )
            return pipeline_func

        elif orchestrator == 'beam':
            from tfx.orchestration.beam.beam_dag_runner import BeamDagRunner
            import os
            # for local runs we add the env variable here
            os.environ[ZENML_PIPELINE_CONFIG] = str_config
            runner = BeamDagRunner(env_spec['orchestration_args'])
            runner.run(created_pipeline)
        elif orchestrator == 'ce':
            from tfx.orchestration.beam.beam_dag_runner import BeamDagRunner
            import os
            # for local runs we add the env variable here
            os.environ[ZENML_PIPELINE_CONFIG] = str_config
            runner = CERunner(env_spec[GlobalKeys.API_ARGS_][APIKeys.TOKEN_],
                              env_spec[GlobalKeys.API_ARGS_][APIKeys.HOST_],
                              env_spec[GlobalKeys.API_ARGS_][
                                  APIKeys.ENDPOINT_],
                              env_spec['orchestration_args'])
            runner.run(created_pipeline)
        else:
            raise Exception('What the hell is wrong with you?')


if __name__ == "__main__":
    # TODO: [LOW] Write a way to run this independantly.
    pass
