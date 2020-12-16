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
import os
from typing import Text

import click
import nbformat as nbf

from zenml.utils.constants import APP_NAME, EVALUATION_NOTEBOOK, \
    COMPARISON_NOTEBOOK
from zenml.utils.evaluation_utils import get_eval_block, get_model_block, \
    import_block, info_block, application_block, interface_block


def view_statistics(artifact_uri, magic: bool = False):
    """
    Args:
        artifact_uri (Text):
        magic (bool):
    """
    import os
    import tensorflow as tf
    from tensorflow_metadata.proto.v0 import statistics_pb2
    import panel as pn

    result = {}
    for split in os.listdir(artifact_uri):
        stats_path = os.path.join(artifact_uri, split, 'stats_tfrecord')
        serialized_stats = next(
            tf.compat.v1.io.tf_record_iterator(stats_path))
        stats = statistics_pb2.DatasetFeatureStatisticsList()
        stats.ParseFromString(serialized_stats)
        dataset_list = statistics_pb2.DatasetFeatureStatisticsList()
        for i, d in enumerate(stats.datasets):
            d.name = split
            dataset_list.datasets.append(d)
        result[split] = dataset_list
    h = get_statistics_html(result)

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

    html_template = """<iframe id='facets-iframe' width="100%" height="500px"></iframe>
        <script>
        facets_iframe = document.getElementById('facets-iframe');
        facets_html = '<script src="https://cdnjs.cloudflare.com/ajax/libs/webcomponentsjs/1.3.3/webcomponents-lite.js"><\/script><link rel="import" href="https://raw.githubusercontent.com/PAIR-code/facets/master/facets-dist/facets-jupyter.html"><facets-overview proto-input="protostr"></facets-overview>';
        facets_iframe.srcdoc = facets_html;
         facets_iframe.id = "";
         setTimeout(() => {
           facets_iframe.setAttribute('height', facets_iframe.contentWindow.document.body.offsetHeight + 'px')
         }, 1500)
         </script>"""

    # pylint: enable=line-too-long
    html = html_template.replace('protostr', protostr)
    return html


def get_schema_proto(artifact_uri: Text):
    from google.protobuf import text_format
    from tensorflow.python.lib.io import file_io
    from tensorflow_metadata.proto.v0 import schema_pb2

    schema_path = os.path.join(artifact_uri, 'schema.pbtxt')
    schema = schema_pb2.Schema()
    contents = file_io.read_file_to_string(schema_path)
    schema = text_format.Parse(contents, schema)
    return schema


def evaluate_single_pipeline(trainer_path: Text, eval_path: Text,
                             magic: bool = False):
    # Resolve the pipeline run_id
    """
    Args:
        pipeline_name (Text):
        magic (bool):
    """

    # Patch to make it work locally
    import json
    with open(os.path.join(eval_path, 'eval_config.json'), 'r') as f:
        eval_config = json.load(f)
    eval_config['modelLocations'][''] = eval_path
    with open(os.path.join(eval_path, 'eval_config.json'), 'w') as f:
        json.dump(eval_config, f)

    if magic:
        from zenml.utils.shell_utils import create_new_cell
        model_block = get_model_block(trainer_path)
        eval_block = get_eval_block(eval_path)

        create_new_cell(eval_block)
        create_new_cell(model_block)

    else:
        nb = nbf.v4.new_notebook()
        nb['cells'] = [
            nbf.v4.new_code_cell(get_model_block(trainer_path)),
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
