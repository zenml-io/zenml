from zenml.integrations.aws.flavors.aws_batch_step_operator_flavor import AWSBatchStepOperatorSettings

def test_aws_batch_step_operator_settings():
    AWSBatchStepOperatorSettings(
        job_queue_name='test-job-queue',
        environment={"key_1":"value_1","key_2":"value_2"},
        timeout_seconds=3600
    )