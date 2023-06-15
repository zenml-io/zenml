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
"""Entrypoint for the scheduled vertex job."""
import json
import logging
import random
from typing import TYPE_CHECKING

from google.cloud import aiplatform

if TYPE_CHECKING:
    from flask import Request


# Constants for the scheduler

TEMPLATE_PATH = "template_path"
JOB_ID = "job_id"
PIPELINE_ROOT = "pipeline_root"
PARAMETER_VALUES = "parameter_values"
ENABLE_CACHING = "enable_caching"
ENCRYPTION_SPEC_KEY_NAME = "encryption_spec_key_name"
LABELS = "labels"
PROJECT = "project"
LOCATION = "location"
WORKLOAD_SERVICE_ACCOUNT = "workload_service_account"
NETWORK = "network"


def trigger_vertex_job(request: "Request") -> str:
    """Processes the incoming HTTP request.

    Args:
        request: HTTP request object.

    Returns:
        The response text or any set of values that can be turned into a Response.
    """
    # decode http request payload and translate into JSON object
    request_str = request.data.decode("utf-8")
    request_json = json.loads(request_str)

    display_name = f"{request_json[JOB_ID]}-scheduled-{random.Random().getrandbits(32):08x}"

    run = aiplatform.PipelineJob(
        display_name=display_name,
        template_path=request_json[TEMPLATE_PATH],
        job_id=display_name,
        pipeline_root=request_json[PIPELINE_ROOT],
        parameter_values=request_json[PARAMETER_VALUES],
        enable_caching=request_json[ENABLE_CACHING],
        encryption_spec_key_name=request_json[ENCRYPTION_SPEC_KEY_NAME],
        labels=request_json[LABELS],
        project=request_json[PROJECT],
        location=request_json[LOCATION],
    )

    workload_service_account = request_json[WORKLOAD_SERVICE_ACCOUNT]
    network = request_json[NETWORK]

    if workload_service_account:
        logging.info(
            "The Vertex AI Pipelines job workload will be executed "
            "using the `%s` "
            "service account.",
            workload_service_account,
        )

    if network:
        logging.info(
            "The Vertex AI Pipelines job will be peered with the `%s` "
            "network.",
            network,
        )

    run.submit(
        service_account=workload_service_account,
        network=network,
    )
    return f"{display_name} submitted!"
