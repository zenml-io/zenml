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

import datetime
import os
import re
import shutil
from distutils.core import run_setup

from tfx.orchestration import metadata
from tfx.orchestration.kubeflow.proto import kubeflow_pb2
from tfx.utils import io_utils
from zenml.utils.standards import standard_environment as std_env

from zenml.utils.constants import TrainingTypes


def prepare_sdist():
    """Refer to the README.md in the docs folder"""
    dist_path = os.path.join(os.getcwd(), 'dist')

    if os.path.exists(dist_path) and os.path.isdir(dist_path):
        print('Removing {}'.format(dist_path))
        shutil.rmtree(dist_path)
    else:
        print('There is no dist folder.')

    # FOR THE BOPA
    run_setup('setup.py', script_args=['sdist'])
    req_path = os.path.join(dist_path, 'requirements.txt')
    io_utils.write_string_file(req_path, '')

    # FOR THE BEPA
    run_setup('setup.py', script_args=['sdist'])
    req_path = os.path.join(dist_path, 'requirements.txt')
    io_utils.write_string_file(req_path, '')


def create_experiment_json(experiment_dict, env_spec):
    # Add the bq args which resides in the env dict to the exp dict
    # We have to do this because SplitGen gets bq_args from exp_config for now
    """
    Args:
        experiment_dict:
        env_spec:
    """
    experiment_dict['bq_args'] = env_spec['bq_args']

    ### OUTDATED: TO BE REVISITED SOMETIME ###
    # Save the resulting JSON config file inside the GDP package
    # import json
    # gdp_path = os.path.join(os.getcwd(),
    #                         PACKAGE_NAME,
    #                         'experiment.config.json')
    # with open(gdp_path, 'w') as f:
    #     json.dump(experiment_dict, f)
    return experiment_dict


def create_metadata_connection_config(metadata_args,
                                      pipeline_name,
                                      output_base_dir):
    """Converts yaml metadata args to a ML Metadata config instance according to
    type specified in the yaml. For now, sqlite and mysql are supported.

    Args:
        metadata_args: dict specified in the config.yml
        pipeline_name: str, name of the pipeline
        output_base_dir: str, the path to the output directory

    Returns:
        instance of type metadata_store_pb2.ConnectionConfig
    """
    if metadata_args[std_env.MetadataKeys.TYPE] == 'mysql':
        return metadata.mysql_metadata_connection_config(
            host=metadata_args[std_env.MetadataKeys.HOST_],
            port=metadata_args[std_env.MetadataKeys.PORT_],
            database=metadata_args[std_env.MetadataKeys.DATABASE_],
            username=metadata_args[std_env.MetadataKeys.USERNAME_],
            password=metadata_args[std_env.MetadataKeys.PASSWORD_]
        )
    elif metadata_args[std_env.MetadataKeys.TYPE] == 'kubeflow_mysql':
        # metadata_config = \
        #     kubeflow_dag_runner.get_default_kubeflow_metadata_config()

        metadata_config = kubeflow_pb2.KubeflowMetadataConfig()
        metadata_config.mysql_db_service_host.value = metadata_args[
            std_env.MetadataKeys.HOST_]
        metadata_config.mysql_db_service_port.value = str(
            metadata_args[std_env.MetadataKeys.PORT_])
        metadata_config.mysql_db_name.value = metadata_args[
            std_env.MetadataKeys.DATABASE_]
        metadata_config.mysql_db_user.value = metadata_args[
            std_env.MetadataKeys.USERNAME_]
        metadata_config.mysql_db_password.value = metadata_args[
            std_env.MetadataKeys.PASSWORD_]
        return metadata_config
    elif metadata_args[std_env.MetadataKeys.TYPE] == 'sqlite':
        db_path = os.path.join(output_base_dir,
                               'database',
                               pipeline_name,
                               'metadata.db')
        return metadata.sqlite_metadata_connection_config(db_path)
    else:
        raise AttributeError('Unsupported metadata db type. Choose one of '
                             '"mysql" or "sqlite"')


def parse_yaml_beam_args(pipeline_args):
    """Converts yaml beam args to list of args TFX accepts

    Args:
        pipeline_args: dict specified in the config.yml

    Returns:
        list of strings, where each string is a beam argument
    """
    return ['--{}={}'.format(key, value) for key, value in
            pipeline_args.items()]


def generate_unique_name(base_name):
    """
    Args:
        base_name:
    """
    identifier = os.getenv('CI_COMMIT_SHORT_SHA', os.getenv('USER', 'local'))
    return re.sub(
        r'[^0-9a-zA-Z-]+',
        '-',
        '{pipeline_name}-{identifier}-{ts}'.format(
            pipeline_name=base_name,
            identifier=identifier,
            ts=int(datetime.datetime.timestamp(datetime.datetime.now()))
        ).lower()
    )


def add_ce_env(env_var_name: str, env_var_value: str):
    """A function thats lets you inject environment variable inside a pod in
    Kubeflow

    Args:
        env_var_name (str):
        env_var_value (str):
    """
    import kfp.dsl as dsl
    from kubernetes.client.models import V1EnvVar

    def m(container_op: dsl.ContainerOp):
        env_var = V1EnvVar(name=env_var_name, value=env_var_value)
        container_op.container.add_env_variable(env_var)

    return m


def check_config(env_dict):
    """
    Args:
        env_dict:
    """
    std_env.GlobalKeys.key_check(env_dict)

    std_env.BigQueryKeys.key_check(env_dict[std_env.GlobalKeys.BQ_ARGS])

    std_env.OrchestratorKeys.key_check(
        env_dict[std_env.GlobalKeys.ORCHESTRATION])
    orchestrator = env_dict[std_env.GlobalKeys.ORCHESTRATION][
        std_env.OrchestratorKeys.TYPE]
    orchestrator_args = env_dict[std_env.GlobalKeys.ORCHESTRATION][
        std_env.OrchestratorKeys.ARGS]
    if orchestrator == 'beam':
        std_env.BeamKeys.key_check(orchestrator_args)
    elif orchestrator == 'kubeflow':
        std_env.KubeflowKeys.key_check(orchestrator_args)
    elif orchestrator == 'ce':
        pass
    else:
        raise AssertionError('Unknown type for the orchestration!')

    std_env.TrainingKeys.key_check(env_dict[std_env.GlobalKeys.TRAINING])
    training_type = env_dict[std_env.GlobalKeys.TRAINING][
        std_env.TrainingKeys.TYPE]
    training_args = env_dict[std_env.GlobalKeys.TRAINING][
        std_env.TrainingKeys.ARGS]
    if training_type == TrainingTypes.gcaip.name:
        std_env.AIPlatformKeys.key_check(training_args)
        tiers = ['BASIC', 'STANDARD_1', 'PREMIUM_1', 'BASIC_GPU',
                 'BASIC_TPU', 'CUSTOM']
        assert training_args[std_env.AIPlatformKeys.SCALE_TIER] in tiers, \
            'Invalid scale tier. Select one from {}'.format(tiers)
    elif training_type == TrainingTypes.local.name:
        pass
    else:
        raise AssertionError('Unknown type {} for the training! Choose either'
                             'local or gcaip.'.format(training_type))

    std_env.BeamKeys.key_check(env_dict[std_env.GlobalKeys.EXECUTION])

    std_env.MetadataKeys.key_check(env_dict[std_env.GlobalKeys.METADATA_ARGS])
