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

import logging

from google.cloud import scheduler


def create_scheduler_job(
    project: str,
    region: str,
    http_uri: str,
    body: dict,
    schedule: str = "* * * * *",
    time_zone: str = "America/Los_Angeles",
) -> dict:
    """Creates a Google Cloud Scheduler job that hits a HTTP URI on a schedule.

    Args:
        project: GCP project ID.
        region: GCP region.
        http_uri (str): _description_
        body (dict): _description_
        schedule (str, optional): _description_. Defaults to "* * * * *".
        time_zone (str, optional): _description_. Defaults to "America/Los_Angeles".

    Returns:
        dict: Response from create_job scheduler API.
    """

    # Create a client.
    client = scheduler.CloudSchedulerClient()

    # Construct the fully qualified location path.
    parent = f"projects/{project}/locations/{region}"

    # Construct the request body.
    job = {
        "httpTarget": {
            "uri": http_uri,
            "body": body,
        },
        "httpMethod": "POST",
        "schedule": schedule,
        "time_zone": time_zone,
    }

    # Use the client to send the job creation request.
    response = client.create_job(request={"parent": parent, "job": job})

    logging.debug("Created scheduler job: {}".format(response.name))
    return response
