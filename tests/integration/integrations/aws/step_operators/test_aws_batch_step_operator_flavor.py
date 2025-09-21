from zenml.integrations.aws.flavors.aws_batch_step_operator_flavor import AWSBatchStepOperatorSettings
from zenml.integrations.aws.step_operators.aws_batch_step_operator import AWSBatchJobDefinition
from zenml import pipeline, step
from zenml.config import DockerSettings
from zenml.client import Client

# Get the ZenML client
client = Client()

def test_aws_batch_step_operator_settings():
    AWSBatchStepOperatorSettings(
        instance_type="g4dn.xlarge",
        environment={"key_1":"value_1","key_2":"value_2"},
        timeout_seconds=60
    )

def test_aws_batch_step_job_definition():
    AWSBatchJobDefinition(
        jobDefinitionName="test-job-name",
    )

# def test_aws_batch_step_operator_step():

#     @step(
#         step_operator="aws_batch",
#         settings={
#             'docker':DockerSettings(parent_image='test-image'),
#             'step_operator':AWSBatchStepOperatorSettings(instance_type='test-instance')
#         }
#     )
#     def test_step(name: str) -> str:
        
#         return f'Hello {name}! I am running on AWS Batch!' 
    
#     @pipeline
#     def test_pipeline(name: str):
#         test_step(name)
    
#     test_pipeline("Sebastian",stack=Client().get_stack("aws_batch_stack"))