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
import random

from flask import Request, Response
from google.cloud import aiplatform

# Constants for the scheduler

TEMPLATE_PATH = "template_path"
JOB_ID = "job_id"
PIPELINE_ROOT = "pipeline_root"
PIPELINE_SPEC_URI = "pipeline_spec_uri"
PARAMETER_VALUES = "parameter_values"
ENABLE_CACHING = "enable_caching"
ENCRYPTION_SPEC_KEY_NAME = "encryption_spec_key_name"
LABELS = "labels"
PROJECT = "project"
LOCATION = "location"


def trigger_vertex_job(request: Request) -> Response:
    """Processes the incoming HTTP request.

    Args:
      request: HTTP request object.

    Returns:
      The response text or any set of values that can be turned into a Response.
    """
    # decode http request payload and translate into JSON object
    request_str = request.data.decode("utf-8")
    request_json = json.loads(request_str)

    # job = aiplatform.PipelineJob(
    #     display_name=f"hello-world-cloud-function-pipeline",
    #     template_path=pipeline_spec_uri,
    #     pipeline_root=PIPELINE_ROOT,
    #     enable_caching=False,
    #     parameter_values=parameter_values,
    # )
    display_name = (
        f"{request_json[JOB_ID]}_{random.Random().getrandbits(32):08x}"
    )

    run = aiplatform.PipelineJob(
        display_name=display_name,
        template_path=request_json[PIPELINE_SPEC_URI],
        job_id=request_json[JOB_ID],
        pipeline_root=request_json[PIPELINE_ROOT],
        parameter_values=request_json[PARAMETER_VALUES],
        enable_caching=request_json[ENABLE_CACHING],
        encryption_spec_key_name=request_json[ENCRYPTION_SPEC_KEY_NAME],
        labels=request_json[LABELS],
        project=request_json[PROJECT],
        location=request_json[LOCATION],
    )
    run.submit()
    return "Job submitted"
