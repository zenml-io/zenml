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

import base64
import json
import os
from typing import Text

import click
import nbformat as nbf
import pandas as pd
import panel as pn
import tensorflow as tf
import tensorflow_data_validation as tfdv
import tensorflow_datasets as tfds
from tensorflow_metadata.proto.v0 import statistics_pb2
from tensorflow_transform.tf_metadata import schema_utils
from tfx.utils import io_utils

from zenml.core.repo.repo import Repository
from zenml.utils.constants import APP_NAME, EVALUATION_NOTEBOOK, \
    COMPARISON_NOTEBOOK
from zenml.utils.enums import GDPComponent
from zenml.utils.path_utils import read_file_contents
from zenml.utils.post_training.evaluation_utils import get_eval_block, \
    get_tensorboard_block, \
    import_block, info_block, application_block, interface_block


def get_statistics_html(stats_dict):
    """
    Args:
        stats_dict:
    """
    from tensorflow_metadata.proto.v0 import statistics_pb2

    combined_statistics = statistics_pb2.DatasetFeatureStatisticsList()

    for split, stats in stats_dict.items():
        stats_copy = combined_statistics.datasets.add()
        stats_copy.MergeFrom(stats.datasets[0])
        stats_copy.name = split

    protostr = base64.b64encode(
        combined_statistics.SerializeToString()).decode('utf-8')

    # assumes stats.html in the same folder
    template = \
        os.path.join(os.path.abspath(os.path.dirname(__file__)), 'stats.html')
    html_template = read_file_contents(template)

    # pylint: enable=line-too-long
    html = html_template.replace('protostr', protostr)
    return html


def get_statistics_artifact(pipeline_name: Text, component_name: Text):
    """
    Get statistics artifact from pipeline

    Args:
        pipeline_name: name of pipeline
        component_name: name of statistics component
    """
    return Repository.get_instance().get_artifacts_uri_by_component(
        pipeline_name, component_name)[0]


def get_statistics_dataset_dict(stats_uri: Text):
    """Get DatasetFeatureStatisticsList from stats URI"""
    result = {}
    for split in os.listdir(stats_uri):
        stats_path = os.path.join(stats_uri, split, 'stats_tfrecord')
        serialized_stats = next(
            tf.compat.v1.io.tf_record_iterator(stats_path))
        stats = statistics_pb2.DatasetFeatureStatisticsList()
        stats.ParseFromString(serialized_stats)
        dataset_list = statistics_pb2.DatasetFeatureStatisticsList()
        for i, d in enumerate(stats.datasets):
            d.name = split
            dataset_list.datasets.append(d)
        result[split] = dataset_list
    return result


def view_statistics(artifact_uri, magic: bool = False):
    """
    View statistics in HTML.

    Args:
        artifact_uri (Text):
        magic (bool):
    """
    stats_dict = get_statistics_dataset_dict(artifact_uri)
    h = get_statistics_html(stats_dict)

    if magic:
        import sys
        if 'ipykernel' not in sys.modules:
            raise EnvironmentError(
                'The magic functions are only usable '
                'in a Jupyter notebook.')
        from IPython.core.display import display, HTML
        display(HTML(h))
    else:
        pn.serve(panels=pn.pane.HTML(h, width=1200), show=True)


def detect_anomalies(stats_uri: Text, schema_uri: Text, split_name: Text):
    schema = get_schema_proto(schema_uri)
    stats = get_statistics_dataset_dict(stats_uri)
    if split_name not in stats:
        raise Exception(f'{split_name} split not present!')
    anomalies = tfdv.validate_statistics(stats[split_name], schema)
    tfdv.display_anomalies(anomalies)


def view_schema(uri: Text):
    """
    View schema .

    Args:
        uri: URI to schema.
    """
    schema = get_schema_proto(uri)

    # TODO: [LOW] Replace with our own function
    tfdv.display_schema(schema=schema)


def get_schema_proto(artifact_uri: Text):
    schema_path = os.path.join(artifact_uri, 'schema.pbtxt')
    schema = io_utils.SchemaReader().read(schema_path)
    return schema


def get_schema_artifact(pipeline_name: Text, component_name: Text):
    """
    Get schema artifact from pipeline

    Args:
        pipeline_name: name of pipeline
        component_name: name of schema component
    """
    return Repository.get_instance().get_artifacts_uri_by_component(
        pipeline_name, component_name)[0]


def get_feature_spec_from_schema(pipeline_name: Text, component_name: Text):
    """
    Get schema artifact from pipeline

    Args:
        pipeline_name: name of pipeline
        component_name: name of schema component
    """
    schema_proto = get_schema_proto(
        get_schema_artifact(pipeline_name, component_name))
    spec = schema_utils.schema_as_feature_spec(schema_proto).feature_spec
    return spec


def get_parsed_dataset(dataset, spec):
    """
    Takes tf.data.Dataset and parses it based on spec

    Args:
        dataset: a tf.data.Dataset object
        spec: the spec to parse from
    """

    def parse(raw_record):
        return tf.io.parse_example(raw_record, spec)

    dataset = dataset.map(parse)
    return dataset


def convert_data_to_numpy(dataset, sample_size):
    """
    Takes tf.data.Dataset and converts to numpy array.

    Args:
        dataset: a tf.data.Dataset object
        sample_size: number of rows to limit to
    """
    np_dataset = tfds.as_numpy(dataset)
    data = []
    for i, d in enumerate(np_dataset):
        if i == sample_size:
            break
        new_row = {k: v[0] for k, v in d.items()}
        new_row = {k: v if type(v) != bytes else v.decode()
                   for k, v in new_row.items()}
        data.append(new_row)
    return data


def convert_raw_dataset_to_pandas(dataset, spec, sample_size):
    """
    Takes tf.data.Dataset and converts to a Pandas DataFrame.

    Args:
        dataset: a tf.data.Dataset object
        spec: the spec to parse from
        sample_size: number of rows to limit to
    """
    dataset = get_parsed_dataset(dataset, spec)
    data = convert_data_to_numpy(dataset, sample_size)
    return pd.DataFrame(data)


def get_pusher_artifact(pipeline_name: Text, component_name: Text = None):
    """
    Get schema artifact from pipeline

    Args:
        pipeline_name: name of pipeline
        component_name: name of pusher component
    """
    component_name = component_name \
        if component_name else GDPComponent.Deployer.name
    return Repository.get_instance().get_artifacts_uri_by_component(
        pipeline_name, component_name)[0]


def create_new_cell(contents):
    """
    Creates new cell in jupyter notebook.

    Args:
        contents: contents of cell.
    """
    import sys
    from IPython.core.getipython import get_ipython

    if 'ipykernel' not in sys.modules:
        raise EnvironmentError('The magic functions are only usable in a '
                               'Jupyter notebook.')

    shell = get_ipython()

    payload = dict(
        source='set_next_input',
        text=contents,
        replace=False,
    )
    shell.payload_manager.write_payload(payload, single=False)


def evaluate_single_pipeline(
        pipeline_name: Text,
        trainer_component_name: Text = None,
        evaluator_component_name: Text = None,
        magic: bool = False):
    """

    Args:
        pipeline_name: name of pipeline.
        trainer_component_name: name of trainer component.
        evaluator_component_name: name of evaluator component.
        magic:
    """
    # Default to the standard names
    trainer_component_name = trainer_component_name \
        if trainer_component_name else GDPComponent.Trainer.name
    evaluator_component_name = evaluator_component_name \
        if evaluator_component_name else GDPComponent.Evaluator.name

    trainer_path = Repository.get_instance().get_artifacts_uri_by_component(
        pipeline_name, trainer_component_name)[0]
    eval_path = Repository.get_instance().get_artifacts_uri_by_component(
        pipeline_name, evaluator_component_name)[0]

    # Patch to make it work locally
    with open(os.path.join(eval_path, 'eval_config.json'), 'r') as f:
        eval_config = json.load(f)
    eval_config['modelLocations'][''] = eval_path
    with open(os.path.join(eval_path, 'eval_config.json'), 'w') as f:
        json.dump(eval_config, f)

    if magic:
        tensorboard_block = get_tensorboard_block(trainer_path)
        eval_block = get_eval_block(eval_path)

        create_new_cell(eval_block)
        create_new_cell(tensorboard_block)
    else:
        nb = nbf.v4.new_notebook()
        nb['cells'] = [
            nbf.v4.new_code_cell(get_tensorboard_block(trainer_path)),
            nbf.v4.new_code_cell(get_eval_block(eval_path))]

        config_folder = click.get_app_dir(APP_NAME)

        if not (os.path.exists(config_folder) and os.path.isdir(
                config_folder)):
            os.makedirs(config_folder)

        final_out_path = os.path.join(config_folder, EVALUATION_NOTEBOOK)
        s = nbf.writes(nb)
        if isinstance(s, bytes):
            s = s.decode('utf8')

        with open(final_out_path, 'w') as f:
            f.write(s)
        os.system('jupyter notebook "{}"'.format(final_out_path))


def compare_multiple_pipelines():
    """
    Args:
        workspace_id (Text):
    """
    info = {}

    # generate notebook
    nb = nbf.v4.new_notebook()
    nb['cells'] = [
        nbf.v4.new_code_cell(import_block()),
        nbf.v4.new_code_cell(info_block(info)),
        nbf.v4.new_code_cell(application_block()),
        nbf.v4.new_code_cell(interface_block()),
    ]

    # write notebook
    config_folder = click.get_app_dir(APP_NAME)

    if not (os.path.exists(config_folder) and os.path.isdir(
            config_folder)):
        os.makedirs(config_folder)

    final_out_path = os.path.join(config_folder, COMPARISON_NOTEBOOK)
    s = nbf.writes(nb)
    if isinstance(s, bytes):
        s = s.decode('utf8')

    with open(final_out_path, 'w') as f:
        f.write(s)

    # serve notebook
    os.system('panel serve "{}" --show'.format(final_out_path))
