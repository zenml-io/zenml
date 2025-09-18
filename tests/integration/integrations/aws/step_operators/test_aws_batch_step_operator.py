#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.


import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.integrations.aws.step_operators.aws_batch_step_operator import AWSBatchStepOperator, get_context

def test_aws_batch_context(monkeypatch):
    """Tests the AWSBatchContext class."""

    monkeypatch.setenv('AWS_BATCH_JOB_MAIN_NODE_INDEX',0)
    monkeypatch.setenv('AWS_BATCH_JOB_MAIN_NODE_PRIVATE_IPV4_ADDRESS','test-address')
    monkeypatch.setenv('AWS_BATCH_JOB_NODE_INDEX',1)
    monkeypatch.setenv('AWS_BATCH_JOB_NUM_NODES',2)

    test_aws_batch_context = get_context()
    assert test_aws_batch_context.main_node_index == 0
    assert test_aws_batch_context.main_node_address == 'test-address'
    assert test_aws_batch_context.node_index == 1
    assert test_aws_batch_context.num_nodes == 2

def test_aws_batch_step_operator_map_environment():
    """Tests the AWSBatchStepOperator's map_environment class method."""

    test_environment = {'key_1':'value_1','key_2':'value_2'}
    expected = [
        {
            "name": "key_1",
            "value": "value_1"
        },
        {
            "name": "key_2",
            "value": "value_2"
        }
    ]

    assert AWSBatchStepOperator.map_environment(test_environment) == expected

@pytest.mark.parametrize(
        "test_resource_settings,expected",
        [
            (
                ResourceSettings(),
                []
            ),
            (
                ResourceSettings(cpu_count=0.4,gpu_count=1,memory="10MiB"),
                [
                    {
                        "value":"1",
                        "type":"VCPU"
                    },
                    {
                        "value":"1",
                        "type":"GPU"
                    },
                    {
                        "value": "10",
                        "type": "MEMORY"
                    }
                ]
            ),
            (
                ResourceSettings(cpu_count=1,gpu_count=1),
                [
                    {
                        "value":"1",
                        "type":"VCPU"
                    },
                    {
                        "value":"1",
                        "type":"GPU"
                    },
                ]
            ),
            (
                ResourceSettings(memory="1GiB"),
                [
                    {
                        "value": "1024",
                        "type": "MEMORY"
                    }
                ]
            ),

        ]
)
def test_aws_batch_step_operator_map_resource_settings(test_resource_settings,expected):
    """Tests the AWSBatchStepOperator's map_resource_settings class method."""

    assert AWSBatchStepOperator.map_resource_settings(test_resource_settings) == expected
