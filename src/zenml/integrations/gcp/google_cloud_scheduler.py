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
"""Utils for the Google Cloud Scheduler API."""

import json
import logging
from typing import TYPE_CHECKING, Dict, Optional, Union

from google.cloud import scheduler
from google.cloud.scheduler_v1.types import (
    CreateJobRequest,
    HttpMethod,
    HttpTarget,
    Job,
    OidcToken,
)

if TYPE_CHECKING:
    from google.auth.credentials import Credentials


def create_scheduler_job(
    project: str,
    region: str,
    http_uri: str,
    body: Dict[str, Union[Dict[str, str], bool, str, None]],
    credentials: Optional["Credentials"] = None,
    schedule: str = "* * * * *",
    time_zone: str = "Etc/UTC",
) -> None:
    """Creates a Google Cloud Scheduler job.

    Job periodically sends POST request to the specified HTTP URI on a schedule.

    Args:
        project: GCP project ID.
        region: GCP region.
        http_uri: HTTP URI of the cloud function to call.
        body: The body of values to send to the cloud function in the POST call.
        schedule: Cron expression of the schedule. Defaults to "* * * * *".
        time_zone: Time zone of the schedule. Defaults to "Etc/UTC".
        credentials: Credentials to use for GCP services.
    """
    # Create a client.
    client = scheduler.CloudSchedulerClient(credentials=credentials)

    # Construct the fully qualified location path.
    parent = f"projects/{project}/locations/{region}"

    # Use the client to send the job creation request.
    job = client.create_job(
        request=CreateJobRequest(
            parent=parent,
            job=Job(
                http_target=HttpTarget(
                    uri=http_uri,
                    body=json.dumps(body).encode(),
                    http_method=HttpMethod.POST,
                    oidc_token=OidcToken(
                        service_account_email=credentials.signer_email
                        if credentials and hasattr(credentials, "signer_email")
                        else None
                    ),
                ),
                schedule=schedule,
                time_zone=time_zone,
            ),
        )
    )

    logging.debug(f"Created scheduler job. Response: {job}")
