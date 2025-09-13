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
from zenml.integrations.aws.step_operators.aws_batch_step_operator import AWSBatchStepOperator

def test_aws_batch_step_operator_map_environment():
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
    assert AWSBatchStepOperator.map_resource_settings(test_resource_settings) == expected
