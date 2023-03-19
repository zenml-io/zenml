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
"""Implementation of the ZenML AWS VM orchestrator."""

from datetime import datetime, timedelta, timezone
from operator import itemgetter
from typing import TYPE_CHECKING, ClassVar

import boto3

from zenml.integrations.aws import AWS_VM_ORCHESTRATOR_FLAVOR
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

AWS_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
AWS_REGION = "AWS_REGION"

# TODO: Make this configurable
AWS_LOGS_GROUP_NAME = "/zenml/ec2/pipelines"


def stream_logs(stream_name: str, seconds_before: int = 10) -> None:
    """Streams logs onto the logger.

    Args:
        stream_name: Name of stream.
        seconds_before: How many seconds before to stream logs.
    """
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
    """Get a good name from a bad name.

    Args:
        bad_name: Original name of VM.

    Returns:
        A good name for the VM.
    """
    return bad_name.replace("_", "-")


def get_image_from_family() -> str:
    """Retrieve the newest image from the AWS Deep Learning Catalog.

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
    # Sort on Creation date descending
    image_details = sorted(
        response["Images"], key=itemgetter("CreationDate"), reverse=True
    )
    ami_id = image_details[0]["ImageId"]
    return ami_id


# def delete_instance(instance_id: str) -> None:
#     """Send an instance deletion request to the EC2 API and wait for it to complete.

#     Args:
#         instance_id: ID of the EC2 instance.
#     """
#     logger.info(f"Deleting {instance_id}...")
#     instance_client.delete(
#         project=project_id, zone=zone, instance=machine_name
#     )
#     logger.info(f"Instance {machine_name} deleted.")
#     return


def get_instance(
    instance_id: str,
) -> dict:
    """Gets instance from AWS.

    Args:
        instance_id (str): ID of the instance.

    Returns:
        Get instance type.
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
        registry_name (str): Name of registry.
        log_stream_name (str): Name of log stream.

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
        f"{image_name} {c_params} || true\n"
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
    """Send an instance creation request to the Compute Engine API.

    Args:
        executor_image_name (str): temp.
        c_params (str): temp.
        iam_role (str): temp.
        instance_type (str): temp.
        instance_image (str): temp.
        region (str): temp.
        key_name (str): temp.
        security_group (str): temp.
        min_count (str): temp.
        max_count (str): temp.
        registry_name (str): temp.
        log_stream_name (str): temp.

    Returns:
        Instance object.
    """
    startup = get_startup_script(
        region, executor_image_name, c_params, registry_name, log_stream_name
    )

    # TODO: Maybe add more args here or less
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


def setup_session() -> boto3.Session:
    """Sets up a boto3 session.

    Returns:
        A boto session.
    """
    session = boto3.Session()
    # credentials = session.get_credentials()
    # os.environ[AWS_ACCESS_KEY_ID] = credentials.access_key
    # os.environ[AWS_SECRET_ACCESS_KEY] = credentials.secret_key
    return session


class AWSVMOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using AWS VM."""

    # Class Configuration
    FLAVOR: ClassVar[str] = AWS_VM_ORCHESTRATOR_FLAVOR
