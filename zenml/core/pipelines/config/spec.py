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

import os
from typing import Dict, Text, Any

from tfx.extensions.google_cloud_ai_platform.trainer.executor import \
    TRAINING_ARGS_KEY
from tfx.utils import io_utils
from zenml.utils.standards import standard_dataline as std_dl
from zenml.utils.standards import standard_environment as std_env
from zenml.utils.standards import standard_inferline as std_if

from zenml.cli.version import PACKAGE_VERSION, PACKAGE_NAME
from zenml.utils.constants import TRAINER_IMAGE
from zenml.utils.constants import TrainingTypes


def get_pipeline_spec(env_dict):
    # Checking the global keys
    """
    Args:
        env_dict:
    """
    check_config(env_dict)

    # Dataset, experiment
    experiment_name = env_dict[std_env.GlobalKeys.EXPERIMENT_NAME]
    run_name = generate_unique_name(experiment_name)

    # Output
    output_base_dir = env_dict[std_env.GlobalKeys.OUTPUT_BASE_DIR]
    if not output_base_dir.startswith('gs://'):
        output_base_dir = os.path.abspath(output_base_dir)

    # Pipeline settings
    pipeline_name = experiment_name
    pipeline_enable_cache = env_dict[std_env.GlobalKeys.ENABLE_CACHE]
    project_id = env_dict[std_env.GlobalKeys.PROJECT_ID]
    gcp_region = env_dict[std_env.GlobalKeys.GCP_REGION]

    # Pipeline directories
    pipeline_root = os.path.join(output_base_dir, experiment_name)
    pipeline_log = os.path.join(pipeline_root, 'logs', run_name)
    pipeline_temp = os.path.join(pipeline_root, 'tmp', run_name)
    serving_model_dir = os.path.join(pipeline_root, 'serving_model', run_name)

    flags_to_add = {'project': project_id,
                    'region': gcp_region,
                    'temp_location': pipeline_temp,
                    'staging_location': pipeline_temp}

    # Orchestrator
    orch = env_dict[std_env.GlobalKeys.ORCHESTRATION][
        std_env.OrchestratorKeys.TYPE]
    orch_args = env_dict[std_env.GlobalKeys.ORCHESTRATION][
        std_env.OrchestratorKeys.ARGS]

    api_args = {}
    if orch == 'beam':
        orch_args['setup_file'] = os.path.join(os.getcwd(), 'setup.py')
        orch_args['job_name'] = 'gdp-' + run_name
        orch_args.update(flags_to_add)
        orch_args = parse_yaml_beam_args(orch_args)
    elif orch == 'gcp':
        pass
    elif orch == 'ce':
        api_args = env_dict[std_env.GlobalKeys.API_ARGS_]
        orch_args['setup_file'] = os.path.join(os.getcwd(), 'setup.py')
        orch_args['job_name'] = 'gdp-' + run_name
        orch_args.update(flags_to_add)
        orch_args = parse_yaml_beam_args(orch_args)
    elif orch == 'kubeflow':
        # TODO: Kubeflow specific stuff here
        pass
    else:
        raise AssertionError('Unknown orchestrator!')

    # BEPA
    exec_args = env_dict[std_env.GlobalKeys.EXECUTION]
    dist_path = os.path.join(os.getcwd(), 'dist')

    # Need to add empty requirements because of TFX bug in dependency_utils.py
    req_path = os.path.join(dist_path, 'requirements.txt')
    io_utils.write_string_file(req_path, '')
    exec_args['requirements_file'] = req_path

    gz_path = os.path.join(dist_path, '{}-{}.tar.gz'.format(
        PACKAGE_NAME,
        PACKAGE_VERSION))
    exec_args['extra_package'] = gz_path

    exec_args.update(flags_to_add)
    exec_args = parse_yaml_beam_args(exec_args)

    # BigQuery Settings
    try:
        bq_args = env_dict[std_env.GlobalKeys.BQ_ARGS]
        if 'project' not in bq_args:
            bq_args['project'] = project_id
        if 'table' not in bq_args:
            bq_args['table'] = experiment_name
    except AttributeError:
        bq_args = {}

    # Metadata Store
    metadata_connection_config = create_metadata_connection_config(
        env_dict[std_env.GlobalKeys.METADATA_ARGS],
        pipeline_name,
        output_base_dir)

    # Training
    training = env_dict[std_env.GlobalKeys.TRAINING]

    training_type = training[std_env.TrainingKeys.TYPE]
    training_args = training[std_env.TrainingKeys.ARGS]

    ai_platform_training_args = {
        'project': project_id,
        'region': gcp_region,
        'jobDir': pipeline_temp,
        'masterConfig': {
            'imageUri':
                TRAINER_IMAGE
        }
    }

    if training_type == TrainingTypes.gcaip.name:
        ai_platform_training_args['project'] = project_id

        ai_platform_training_args['scaleTier'] = training_args[
            std_env.AIPlatformKeys.SCALE_TIER]

        if std_env.AIPlatformKeys.RUNTIME_VERSION_ in training_args:
            ai_platform_training_args['runtimeVersion'] = training_args[
                std_env.AIPlatformKeys.RUNTIME_VERSION_]

        if std_env.AIPlatformKeys.PYTHON_VERSION_ in training_args:
            ai_platform_training_args['pythonVersion'] = training_args[
                std_env.AIPlatformKeys.PYTHON_VERSION_]

        if std_env.AIPlatformKeys.MAX_RUNNING_TIME_ in training_args:
            ai_platform_training_args['scheduling'] = {
                'maxRunningTime': training_args[
                    std_env.AIPlatformKeys.MAX_RUNNING_TIME_]}

    # Serving
    serving = env_dict[std_env.GlobalKeys.SERVING]

    serving_type = serving[std_env.ServingKeys.TYPE]
    ai_platform_serving_args = {
        'model_name': 'model_' + experiment_name.replace('-', '_'),
        'project_id': project_id
    }

    test_mode = env_dict[std_env.GlobalKeys.TEST_MODE]

    return {
        'pipeline_name': pipeline_name,
        'pipeline_root': pipeline_root,
        'pipeline_enable_cache': pipeline_enable_cache,
        'pipeline_log_root': pipeline_log,
        TRAINING_ARGS_KEY: ai_platform_training_args,
        'ai_platform_serving_args': ai_platform_serving_args,
        'metadata_connection_config': metadata_connection_config,
        'orchestrator': orch,
        'orchestration_args': orch_args,
        'execution_args': exec_args,
        'bq_args': bq_args,
        'training_type': training_type,
        'serving_type': serving_type,
        'serving_model_dir': serving_model_dir,
        'test_mode': test_mode,
        std_env.GlobalKeys.API_ARGS_: api_args,
    }


def get_dataline_spec(dataline_config: Dict[Text, Any]):
    """
    Args:
        dataline_config:
    """
    datasource = dataline_config[std_dl.DatalineKeys.DATASOURCE]
    destination = dataline_config[std_dl.DatalineKeys.DESTINATION]
    schema = dataline_config[std_dl.DatalineKeys.SCHEMA_]

    # Pipeline settings
    pipeline_name = dataline_config[std_dl.DatalineKeys.EXPERIMENT_NAME]
    pipeline_enable_cache = dataline_config[std_dl.DatalineKeys.ENABLE_CACHE]
    project_id = dataline_config[std_dl.DatalineKeys.GCP_PROJECT]
    gcp_region = dataline_config[std_dl.DatalineKeys.GCP_REGION]

    # Pipeline directories
    output_base_dir = dataline_config[std_dl.DatalineKeys.OUTPUT_BASE_DIR]
    if not output_base_dir.startswith('gs://'):
        output_base_dir = os.path.abspath(output_base_dir)

    pipeline_root = os.path.join(output_base_dir, pipeline_name)
    run_name = generate_unique_name(pipeline_name)
    pipeline_log = os.path.join(pipeline_root, 'logs', run_name)
    pipeline_temp = os.path.join(pipeline_root, 'tmp', run_name)

    # Orchestrator
    orch = dataline_config[std_dl.DatalineKeys.ORCHESTRATION][
        std_dl.OrchestratorKeys.TYPE]
    orch_args = dataline_config[std_dl.DatalineKeys.ORCHESTRATION][
        std_dl.OrchestratorKeys.ARGS]

    flags_to_add = {'project': project_id,
                    'region': gcp_region,
                    'temp_location': pipeline_temp,
                    'staging_location': pipeline_temp}

    api_args = {}
    if orch == 'beam':
        orch_args['setup_file'] = os.path.join(os.getcwd(), 'setup.py')
        orch_args['job_name'] = 'gdp-' + run_name
        orch_args.update(flags_to_add)
        orch_args = parse_yaml_beam_args(orch_args)
    elif orch == 'gcp':
        pass
    elif orch == 'ce':
        orch_args['setup_file'] = os.path.join(os.getcwd(), 'setup.py')
        orch_args['job_name'] = 'gdp-' + run_name
        orch_args.update(flags_to_add)
        orch_args = parse_yaml_beam_args(orch_args)
        api_args = dataline_config[std_env.GlobalKeys.API_ARGS_]
    elif orch == 'kubeflow':
        # TODO: Kubeflow specific stuff here
        pass
    else:
        raise AssertionError('Unknown orchestrator!')

    # Executor
    exec_args = dataline_config[std_dl.DatalineKeys.EXECUTION]
    dist_path = os.path.join(os.getcwd(), 'dist')

    # Need to add empty requirements because of TFX bug in dependency_utils.py
    req_path = os.path.join(dist_path, 'requirements.txt')
    io_utils.write_string_file(req_path, '')
    exec_args['requirements_file'] = req_path

    exec_args['extra_package'] = '/tfx-src/dist/{}-{}.tar.gz'.format(
        PACKAGE_NAME,
        PACKAGE_VERSION)
    exec_args.update(flags_to_add)
    exec_args = parse_yaml_beam_args(exec_args)

    # Metadata Store
    metadata_config = create_metadata_connection_config(
        dataline_config[std_dl.DatalineKeys.METADATA_ARGS],
        pipeline_name,
        output_base_dir)

    return {
        'pipeline_name': pipeline_name,
        'pipeline_root': pipeline_root,
        'pipeline_enable_cache': pipeline_enable_cache,
        'pipeline_log_root': pipeline_log,
        'metadata_connection_config': metadata_config,
        'orchestrator': orch,
        'orchestration_args': orch_args,
        'execution_args': exec_args,
        'datasource': datasource,
        'destination': destination,
        'schema': schema,
        std_env.GlobalKeys.API_ARGS_: api_args,
    }


def get_inferline_spec(inferline_config):
    """
    Args:
        inferline_config:
    """
    std_if.InferlineKeys.key_check(inferline_config)

    bq_args = inferline_config[std_if.InferlineKeys.BQ_ARGS]
    train_args = inferline_config[std_if.InferlineKeys.TRAIN_CONFIG]
    model_uri = inferline_config[std_if.InferlineKeys.MODEL_URI]
    schema_uri = inferline_config[std_if.InferlineKeys.SCHEMA_URI]

    # Pipeline settings
    pipeline_name = inferline_config[std_if.InferlineKeys.EXPERIMENT_NAME]
    pipeline_enable_cache = inferline_config[std_if.InferlineKeys.ENABLE_CACHE]
    project_id = inferline_config[std_if.InferlineKeys.PROJECT_ID]
    gcp_region = inferline_config[std_if.InferlineKeys.GCP_REGION]

    # Pipeline directories
    output_base_dir = inferline_config[std_if.InferlineKeys.OUTPUT_BASE_DIR]
    if not output_base_dir.startswith('gs://'):
        output_base_dir = os.path.abspath(output_base_dir)

    pipeline_root = os.path.join(output_base_dir, pipeline_name)
    run_name = generate_unique_name(pipeline_name)
    pipeline_log = os.path.join(pipeline_root, 'logs', run_name)
    pipeline_temp = os.path.join(pipeline_root, 'tmp', run_name)

    # Orchestrator
    orch_dict = inferline_config[std_if.InferlineKeys.ORCHESTRATION]

    orch = orch_dict[std_dl.OrchestratorKeys.TYPE]
    orch_args = orch_dict[std_dl.OrchestratorKeys.ARGS]

    flags_to_add = {'project': project_id,
                    'region': gcp_region,
                    'temp_location': pipeline_temp,
                    'staging_location': pipeline_temp}

    api_args = {}
    if orch == 'beam':
        orch_args['setup_file'] = os.path.join(os.getcwd(), 'setup.py')
        orch_args['job_name'] = 'gdp-' + run_name
        orch_args.update(flags_to_add)
        orch_args = parse_yaml_beam_args(orch_args)
    elif orch == 'gcp':
        pass
    elif orch == 'ce':
        api_args = inferline_config[std_env.GlobalKeys.API_ARGS_]
        orch_args['setup_file'] = os.path.join(os.getcwd(), 'setup.py')
        orch_args['job_name'] = 'gdp-' + run_name
        orch_args.update(flags_to_add)
        orch_args = parse_yaml_beam_args(orch_args)
    elif orch == 'kubeflow':
        # TODO: Kubeflow specific stuff here
        pass
    else:
        raise AssertionError('Unknown orchestrator!')

    # Executor
    exec_args = inferline_config[std_if.InferlineKeys.EXECUTION]
    exec_args['extra_package'] = '/tfx-src/dist/{}-{}.tar.gz'.format(
        PACKAGE_NAME,
        PACKAGE_VERSION)
    exec_args.update(flags_to_add)
    exec_args = parse_yaml_beam_args(exec_args)

    # Metadata Store
    metadata_config = create_metadata_connection_config(
        inferline_config[std_if.InferlineKeys.METADATA_ARGS],
        pipeline_name,
        output_base_dir)

    return {
        'pipeline_name': pipeline_name,
        'pipeline_root': pipeline_root,
        'pipeline_enable_cache': pipeline_enable_cache,
        'pipeline_log_root': pipeline_log,
        'metadata_connection_config': metadata_config,
        'orchestrator': orch,
        'orchestration_args': orch_args,
        'execution_args': exec_args,
        'bq_args': bq_args,
        'train_config': train_args,
        'model_uri': model_uri,
        'schema_uri': schema_uri,
        std_env.GlobalKeys.API_ARGS_: api_args,
    }
