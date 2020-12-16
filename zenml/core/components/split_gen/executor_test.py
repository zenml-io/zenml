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

import tensorflow as tf
import yaml
from tfx.components.base.base_executor import BaseExecutor
from tfx import types

from zenml.core.components.split_gen.executor import Executor

"""Test for the custom bigquery_pusher executor"""


class ExecutorTest(tf.test.TestCase):

    def setUp(self):
        """
        Setting up the input dict, output dict and exec parameters
        """
        self.input_dict = {}

        with open('/home/hamza/workspace/maiot/gdp/config.yaml') as f:
            experiment_dict = yaml.load(f)['experiment']
        group = experiment_dict['asset_groups']['horizontal_group_1']

        # Create execution parameters
        _bq_args = {
            'project': 'maiot-machine-learning',
            'dataset': 'adac_kasasi',
            'table': 'tfx_test'
        }

        self.exec_properties = {
            'bq_args': _bq_args,
            'group_yaml': group
        }

        # TODO: [LOW] To be updated
        self.output_dict = {
            'examples': [types.Artifact('ExamplesPath', split=split_name)
            for split_name in ['train', 'eval']]
        }
        # Creating a context for the executors to run the tests locally
        # TODO: Does not work with dataflow somehow
        options = [
            '--job_name=split_gen_executor_test'
            '--runner=DataflowRunner',
            '--project=maiot-machine-learning',
            '--temp_location=gs://adac_kasasi/tfx/split_gen/test/'
        ]
        self.context = BaseExecutor.Context(options)

    def testDo(self):
        # Create the executor with the custom context and run it with the
        # test input dict, output dict and exec properties
        split_gen_executor = Executor(self.context)
        split_gen_executor.Do(self.input_dict,
                              self.output_dict,
                              self.exec_properties)


if __name__ == '__main__':
    tf.test.main()
