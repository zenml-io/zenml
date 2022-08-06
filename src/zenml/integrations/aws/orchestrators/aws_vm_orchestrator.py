#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

import os
import time
from datetime import datetime, timedelta, timezone
from operator import itemgetter
from typing import TYPE_CHECKING, Any, ClassVar, List

import boto3
from google.protobuf import json_format
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

from zenml.integrations.aws import AWS_VM_ORCHESTRATOR_FLAVOR
from zenml.integrations.aws.orchestrators.aws_vm_entrypoint_configuration import (
    PB2_PIPELINE_JSON_FILE_PATH,
    RUN_NAME_OPTION,
    AWSVMEntrypointConfiguration,
)
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.repository import Repository
from zenml.utils import yaml_utils
from zenml.utils.docker_utils import get_image_digest
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack
    from zenml.steps import BaseStep

logger = get_logger(__name__)

AWS_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
AWS_REGION = "AWS_REGION"
AWS_LOGS_GROUP_NAME = "zenmlpipelines"


def stream_logs(stream_name: str, seconds_before: int = 10) -> None:
    """Streams logs onto the logger"""
    now = datetime.now(timezone.utc)
    before = now - timedelta(seconds=seconds_before)

    session = setup_session()
    ec2_client = session.client("logs")

    try:
        response = ec2_client.get_log_events(
            logGroupName=AWS_LOGS_GROUP_NAME,
            logStreamName=stream_name,
            startTime=int(before.timestamp() * 1000),
            endTime=int(now.timestamp() * 1000),
            startFromHead=True,
        )
    except Exception:
        return

    # query and print all matching logs
    for entry in response["events"]:
        logger.info(entry["message"])


def sanitize_aws_vm_name(bad_name: str) -> str:
    """Get a good name from a bad name"""
    return bad_name.replace("_", "-")


def get_image_from_family() -> str:
    """
    Retrieve the newest image from the AWS Deep Learning Catalog.

    Returns:
        An AMI ID of the image.
    """
    session = setup_session()
    ec2_client = session.client("ec2")
    response = ec2_client.describe_images(
        Filters=[
            {
                "Name": "name",
                "Values": [
                    "AWS Deep Learning Base AMI*",
                ],
            },
        ],
        Owners=["amazon"],
    )
    # Sort on Creation date Desc
    image_details = sorted(
        response["Images"], key=itemgetter("CreationDate"), reverse=True
    )
    ami_id = image_details[0]["ImageId"]
    return ami_id


def delete_instance(instance_id: str) -> None:
    """
    Send an instance deletion request to the EC2 API and wait for it to complete.

    Args:
        instance_id: ID of the EC2 instance.
    """
    logger.info(f"Deleting {instance_id}...")
    operation = instance_client.delete(
        project=project_id, zone=zone, instance=machine_name
    )
    logger.info(f"Instance {machine_name} deleted.")
    return


def get_instance(
    instance_id: str,
) -> dict:
    """Gets instance from AWS.

    Args:
        instance_id (str): ID of the instance.
    """
    session = setup_session()
    ec2_resource = session.resource("ec2")
    instances = ec2_resource.instances.filter(
        Filters=[{"Name": "instance-id", "Values": [f"{instance_id}"]}]
    )
    for instance in instances:
        return instance


def get_startup_script(
    region: str,
    image_name: str,
    c_params: str,
    registry_name: str,
    log_stream_name: str,
) -> str:
    """Generates a startup script for the VM.

    Args:
        region (str): Region to launch VM.
        image_name (str): Image to run in the VM.
        c_params (str): Params for the container.

    Returns:
        script (str): String to attach to VM on launch.
    """
    return (
        f"#!/bin/bash -xe\n"
        f"exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1\n"
        f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {registry_name}\n"
        f"mkdir -p /tmp/aws_config\n"
        f"touch /tmp/aws_config/config\n"
        f'echo "[default]">>/tmp/aws_config/config\n'
        f'echo "region = {region}">>/tmp/aws_config/config\n'
        f"docker run --log-driver=awslogs --net=host "
        f"--log-opt awslogs-region={region} --log-opt awslogs-group={AWS_LOGS_GROUP_NAME} "
        f"--log-opt awslogs-create-group=true "
        f"--log-opt awslogs-stream={log_stream_name} "
        f"--env AWS_REGION={region} -v /tmp/aws_config:/root/.aws "
        f"{image_name} {c_params}\n"
        f"instanceId=$(curl http://169.254.169.254/latest/meta-data/instance-id/)\n"
        f"aws ec2 terminate-instances --instance-ids $instanceId --region {region}"
    )


def create_instance(
    executor_image_name: str,
    c_params: str,
    iam_role: str,
    instance_type: str,
    instance_image: str,
    region: str,
    key_name: str,
    security_group: str,
    min_count: str,
    max_count: str,
    registry_name: str,
    log_stream_name: str,
) -> dict:
    """
    Send an instance creation request to the Compute Engine API and wait for it to complete.

    Args:
        image_name: The docker image to run when VM starts.
        c_params: The params to run the docker image with.
        project_id: project ID or project number of the Cloud project you want to use.
        zone: name of the zone to create the instance in. For example: "us-west3-b"
        instance_name: name of the new virtual machine (VM) instance.
        registry_name: name of the registry where image is stored
        log_stream_name: name of stream
    Returns:
        Instance object.
    """
    startup = get_startup_script(
        region, executor_image_name, c_params, registry_name, log_stream_name
    )

    args = {
        "ImageId": instance_image,
        "InstanceType": instance_type,
        "IamInstanceProfile": iam_role,
        "MaxCount": max_count,
        "MinCount": min_count,
        "UserData": startup,
    }

    if security_group:
        args["SecurityGroups"] = security_group

    if key_name:
        args["KeyName"] = key_name

    # Create the VM
    session = setup_session()
    ec2_resource = session.resource("ec2")
    instances = ec2_resource.create_instances(**args)
    return instances[0]


def setup_session():
    session = boto3.Session()
    # credentials = session.get_credentials()
    # os.environ[AWS_ACCESS_KEY_ID] = credentials.access_key
    # os.environ[AWS_SECRET_ACCESS_KEY] = credentials.secret_key
    return session


class AWSVMOrchestrator(BaseOrchestrator):
    iam_role: str = "ec2_vm_role"
    instance_type: str = "t3.large"
    instance_image: str = None  # ami-02e9f4e447e4cda79
    custom_executor_image_name: str = None
    region: str = "us-east-1"
    key_name: str = None
    security_group: str = None
    min_count: int = 1
    max_count: int = 1
    """
    Base class for the orchestrator on AWS.
    
    iam_role: the name of the role created in AWS IAM, defaults to ec2_vm_role
    instance_type: the type of the EC2 instance, defaults to t2.micro  instance on EC2
    instance_image: the image for the EC2 instance, defaults to the public image: AWS Deep Learning Base AMI GPU CUDA 11
    custom_executor_image_name: refers to the image with ZenML
    region: the name of the region that AWS is working on
    key_name: the name of the key to be used whilst creating the
    security_group: the name of a selected security group
    min_count: the minimum number of instances, defaults to 1
    max_count: the maximum number of instances, defaults to 1
    """

    # Class Configuration
    FLAVOR: ClassVar[str] = AWS_VM_ORCHESTRATOR_FLAVOR

    def get_docker_image_name(self, pipeline_name: str) -> str:
        """Returns the full docker image name including registry and tag."""

        base_image_name = f"aws-vm-orchestrator:{pipeline_name}"
        container_registry = Repository().active_stack.container_registry

        if container_registry:
            registry_uri = container_registry.uri.rstrip("/")
            return f"{registry_uri}/{base_image_name}"
        else:
            return base_image_name

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Builds a docker image for the current environment and uploads it to
        a container registry if configured.
        """
        from zenml.utils import docker_utils

        image_name = self.get_docker_image_name(pipeline.name)

        requirements = {*stack.requirements(), *pipeline.requirements}

        logger.debug("AWS VM docker image requirements: %s", requirements)

        docker_utils.build_docker_image(
            build_context_path=get_source_root_path(),
            image_name=image_name,
            dockerignore_path=pipeline.dockerignore_file,
            requirements=requirements,
            base_image=self.custom_executor_image_name,
        )

        assert stack.container_registry  # should never happen due to validation
        stack.container_registry.push_image(image_name)

        # Store the docker image digest in the runtime configuration so it gets
        # tracked in the ZenStore
        image_digest = docker_utils.get_image_digest(image_name) or image_name
        runtime_configuration["docker_image"] = image_digest

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List["BaseStep"],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        executor_image_name = self.get_docker_image_name(pipeline.name)
        executor_image_name = (
            get_image_digest(executor_image_name) or executor_image_name
        )

        instance_image = self.instance_image or get_image_from_family()

        if self.security_group is not None:
            security_group = [self.security_group]
        else:
            security_group = self.security_group

        iam_role = {"Name": self.iam_role}

        run_name = runtime_configuration.run_name
        assert run_name

        # Write pb2 pipeline to artifact store
        artifact_store = Repository().active_stack.artifact_store
        pb2_pipeline_json_file_path = os.path.join(
            artifact_store.path, run_name, "pipeline.json"
        )
        yaml_utils.write_json_string(
            pb2_pipeline_json_file_path, json_format.MessageToJson(pb2_pipeline)
        )

        command = AWSVMEntrypointConfiguration.get_entrypoint_command()
        arguments = AWSVMEntrypointConfiguration.get_entrypoint_arguments(
            steps=sorted_steps,
            pb2_pipeline=pb2_pipeline,
            **{
                RUN_NAME_OPTION: run_name,
                PB2_PIPELINE_JSON_FILE_PATH: pb2_pipeline_json_file_path,
            },
        )
        c_params = " ".join(command + arguments)
        registry_uri = Repository().active_stack.container_registry.uri.rstrip(
            "/"
        )
        ###############################################################
        # TODO: Launch a VM with the docker image `image_name` which  #
        # *syncronously executes the `command` with `arguments`       #
        instance = create_instance(
            executor_image_name,
            c_params,
            iam_role,
            self.instance_type,
            instance_image,
            self.region,
            self.key_name,
            security_group,
            self.min_count,
            self.max_count,
            registry_uri,
            run_name,
        )

        instance_id = instance.id

        logger.info(
            f"Instance {instance_id} is booting up. This might take a few minutes..."
        )

        instance.wait_until_running()
        logger.info(
            f"Instance {instance_id} is now running the pipeline. Logs will be streamed soon..."
        )
        instance = get_instance(instance_id)
        seconds_wait = 10
        while instance.state["Name"] not in [
            "stopped",
            "terminated",
            "stopping",
            "shutting-down",
        ]:
            instance = get_instance(instance_id)
            stream_logs(run_name, seconds_before=seconds_wait)
            time.sleep(seconds_wait)
        stream_logs(run_name, seconds_before=seconds_wait)
