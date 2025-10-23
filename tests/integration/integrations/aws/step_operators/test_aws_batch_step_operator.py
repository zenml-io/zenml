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
from pydantic import ValidationError

from zenml.config.resource_settings import ResourceSettings
from zenml.integrations.aws.step_operators.aws_batch_step_operator import (
    AWSBatchStepOperator, 
    ResourceRequirement, 
    AWSBatchJobEC2Definition, 
    AWSBatchJobFargateDefinition,
    AWSBatchJobDefinitionEC2ContainerProperties,
    AWSBatchJobDefinitionFargateContainerProperties,
    VALID_FARGATE_MEMORY,
    VALID_FARGATE_VCPU
)

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
                [
                    ResourceRequirement(value="1",type="VCPU"),
                    ResourceRequirement(value="1024",type="MEMORY")
                ]
            ),
            (
                ResourceSettings(cpu_count=0.25,gpu_count=1,memory="10MiB"),
                [
                    ResourceRequirement(value="0.25",type="VCPU"),
                    ResourceRequirement(value="10",type="MEMORY"),
                    ResourceRequirement(value="1",type="GPU"),
                ]
            ),
        ]
)
def test_aws_batch_step_operator_map_resource_settings(test_resource_settings,expected):
    """Tests the AWSBatchStepOperator's map_resource_settings class method."""

    assert AWSBatchStepOperator.map_resource_settings(test_resource_settings) == expected

@pytest.mark.parametrize(
        "test_name,expected",
        [
            ('valid-name-123abcABC_', 'valid-name-123abcABC_'),
            ('this!is@not"a£valid$name%123','this-is-not-a-valid-name-123')
        ]
)
def test_aws_batch_step_operator_sanitize_name(test_name, expected):
    
    assert AWSBatchStepOperator.sanitize_name(test_name) == expected

@pytest.mark.parametrize(
    "test_requirements,expected",
    [
        (
            [
                ResourceRequirement(value="0.4",type="VCPU"),
                ResourceRequirement(value="100",type="MEMORY"),
                ResourceRequirement(value="1",type="GPU")
            ],[
                ResourceRequirement(value="1",type="VCPU"),
                ResourceRequirement(value="100",type="MEMORY"),
                ResourceRequirement(value="1",type="GPU")
            ]
        ),
        (
            [
                ResourceRequirement(value="1.1",type="VCPU"),
                ResourceRequirement(value="100",type="MEMORY"),
            ],[
                ResourceRequirement(value="2",type="VCPU"),
                ResourceRequirement(value="100",type="MEMORY"),
            ]
        ),
    ]
)
def test_aws_batch_job_definition_ec2_container_properties_resource_validation(test_requirements, expected):
    actual = AWSBatchJobDefinitionEC2ContainerProperties(
            image="test-image",
            command=["test","command"],
            jobRoleArn="test-job-role-arn",
            executionRoleArn="test-execution-role-arn",
            resourceRequirements=test_requirements
        )
    
    assert actual.resourceRequirements == expected

@pytest.mark.parametrize(
    "test_vcpu_memory_indices",
    [
        (i,j) for i in range(len(VALID_FARGATE_VCPU)) for j in range(len(VALID_FARGATE_MEMORY[VALID_FARGATE_VCPU[i]]))
    ]

)
def test_aws_batch_job_definition_fargate_container_properties(test_vcpu_memory_indices):

    vcpu_index, memory_index = test_vcpu_memory_indices
    test_vcpu_value = VALID_FARGATE_VCPU[vcpu_index]
    test_memory_value = VALID_FARGATE_MEMORY[test_vcpu_value][memory_index]

    test_valid_requirements = [
        ResourceRequirement(
            type="VCPU",
            value=test_vcpu_value
        ),
        ResourceRequirement(
            type="MEMORY",
            value=test_memory_value
        )
    ]
    
    AWSBatchJobDefinitionFargateContainerProperties(
        image="test-image",
        command=["test","command"],
        jobRoleArn="test-job-role-arn",
        executionRoleArn="test-execution-role-arn",
        resourceRequirements=test_valid_requirements
    )

@pytest.mark.parametrize(
    "test_invalid_requirements,expected_message",
    [
        (
            [
                ResourceRequirement(
                    type="VCPU",
                    value="invalid-value"
                ),
                ResourceRequirement(
                    type="MEMORY",
                    value="irrelevant-value"
                )
            ],
            "Invalid fargate resource requirement VCPU value*"
        ),
        (
            [
                ResourceRequirement(
                    type="VCPU",
                    value="16" # valid
                    ),
                ResourceRequirement(
                    type="MEMORY",
                    value="invalid-value"
                )
            ],
            "Invalid fargate resource requirement MEMORY value*"
        ),
        (
            [
                ResourceRequirement(
                    type="VCPU",
                    value="irrelevant-value"
                ),
                ResourceRequirement(
                    type="MEMORY",
                    value="irrelevant-value"
                ),
                ResourceRequirement(
                    type="GPU",
                    value="1" # invalid
                )
            ],
            "Invalid fargate resource requirement: GPU. Use EC2*"
        )
    ]
)
def test_aws_batch_job_definition_fargate_container_properties_raise_invalid_requirements(test_invalid_requirements,expected_message):

    with pytest.raises(ValidationError,match=expected_message):
    
        AWSBatchJobDefinitionFargateContainerProperties(
            image="test-image",
            command=["test","command"],
            jobRoleArn="test-job-role-arn",
            executionRoleArn="test-execution-role-arn",
            resourceRequirements=test_invalid_requirements
        )

def test_aws_batch_job_ec2_definition():
    AWSBatchJobEC2Definition(
        jobDefinitionName="test",
        containerProperties=AWSBatchJobDefinitionEC2ContainerProperties(
            image="test-image",
            command=["test","command"],
            jobRoleArn="test-job-role-arn",
            executionRoleArn="test-execution-role-arn",
            resourceRequirements=[
                ResourceRequirement(value="1",type="GPU"),
                ResourceRequirement(value="1",type="VCPU"),
                ResourceRequirement(value="1024",type="MEMORY")
            ]
        )
    )
    
def test_aws_batch_job_fargate_definition():
    AWSBatchJobFargateDefinition(
        jobDefinitionName="test",
        containerProperties=AWSBatchJobDefinitionFargateContainerProperties(
            image="test-image",
            command=["test","command"],
            jobRoleArn="test-job-role-arn",
            executionRoleArn="test-execution-role-arn",
            resourceRequirements=[
                ResourceRequirement(value="0.5",type="VCPU"),
                ResourceRequirement(value="3072",type="MEMORY")
            ]
        )
    )