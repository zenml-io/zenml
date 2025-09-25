#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""ZenML deployers utilities."""

import json
from typing import Any, Dict, Optional, Union
from uuid import UUID

import jsonref
import requests

from zenml.client import Client
from zenml.deployers.exceptions import (
    DeploymentHTTPError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
)
from zenml.enums import DeploymentStatus
from zenml.models import DeploymentResponse
from zenml.steps.step_context import get_step_context
from zenml.utils.json_utils import pydantic_encoder


def get_deployment_input_schema(
    deployment: DeploymentResponse,
) -> Dict[str, Any]:
    """Get the schema for a deployment's input parameters.

    Args:
        deployment: The deployment for which to get the schema.

    Returns:
        The schema for the deployment's input parameters.

    Raises:
        RuntimeError: If the deployment has no associated input schema.
    """
    if (
        deployment.snapshot
        and deployment.snapshot.pipeline_spec
        and deployment.snapshot.pipeline_spec.input_schema
    ):
        return deployment.snapshot.pipeline_spec.input_schema

    raise RuntimeError(
        f"Deployment {deployment.name} has no associated input schema."
    )


def get_deployment_output_schema(
    deployment: DeploymentResponse,
) -> Dict[str, Any]:
    """Get the schema for a deployment's output parameters.

    Args:
        deployment: The deployment for which to get the schema.

    Returns:
        The schema for the deployment's output parameters.

    Raises:
        RuntimeError: If the deployment has no associated output schema.
    """
    if (
        deployment.snapshot
        and deployment.snapshot.pipeline_spec
        and deployment.snapshot.pipeline_spec.output_schema
    ):
        return deployment.snapshot.pipeline_spec.output_schema

    raise RuntimeError(
        f"Deployment {deployment.name} has no associated output schema."
    )


def get_deployment_invocation_example(
    deployment: DeploymentResponse,
) -> Dict[str, Any]:
    """Generate an example invocation command for a deployment.

    Args:
        deployment: The deployment for which to generate an example invocation.

    Returns:
        A dictionary containing the example invocation parameters.
    """
    parameters_schema = get_deployment_input_schema(deployment)

    properties = parameters_schema.get("properties", {})

    if not properties:
        return {}

    parameters = {}

    for attr_name, attr_schema in properties.items():
        parameters[attr_name] = "<value>"
        if not isinstance(attr_schema, dict):
            continue

        default_value = None

        if "default" in attr_schema:
            default_value = attr_schema["default"]
        elif "const" in attr_schema:
            default_value = attr_schema["const"]

        parameters[attr_name] = default_value or "<value>"

    return parameters


def invoke_deployment(
    deployment_name_or_id: Union[str, UUID],
    project: Optional[UUID] = None,
    timeout: int = 300,  # 5 minute timeout
    **kwargs: Any,
) -> Any:
    """Call a deployment and return the result.

    Args:
        deployment_name_or_id: The name or ID of the deployment to call.
        project: The project ID of the deployment to call.
        timeout: The timeout for the HTTP request to the deployment.
        **kwargs: Keyword arguments to pass to the deployment.

    Returns:
        The response from the deployment, parsed as JSON if possible,
        otherwise returned as text.

    Raises:
        DeploymentNotFoundError: If the deployment is not found.
        DeploymentProvisionError: If the deployment is not running
            or has no URL.
        DeploymentHTTPError: If the HTTP request to the endpoint fails.
    """
    client = Client()
    try:
        deployment = client.get_deployment(
            deployment_name_or_id, project=project
        )
    except KeyError:
        raise DeploymentNotFoundError(
            f"Deployment with name or ID '{deployment_name_or_id}' not found"
        )

    if deployment.status != DeploymentStatus.RUNNING:
        raise DeploymentProvisionError(
            f"Deployment {deployment_name_or_id} is not running. Please "
            "refresh or re-deploy the deployment or check its logs for "
            "more details."
        )

    if not deployment.url:
        raise DeploymentProvisionError(
            f"Deployment {deployment_name_or_id} has no URL. Please "
            "refresh the deployment or check its logs for more "
            "details."
        )

    input_schema = None
    if deployment.snapshot and deployment.snapshot.pipeline_spec:
        input_schema = deployment.snapshot.pipeline_spec.input_schema

    if input_schema:
        # Resolve the references in the schema first, otherwise we won't be able
        # to access the data types for object-typed parameters.
        input_schema = jsonref.replace_refs(input_schema)
        assert isinstance(input_schema, dict)

        properties = input_schema.get("properties", {})

        # Some kwargs having one of the collection data types (list, dict) in
        # the schema may be supplied as a JSON string. We need to unpack
        # them before we construct the final JSON payload.
        #
        # We ignore all errors here because they will be better handled by the
        # deployment itself server side.
        for key in kwargs.keys():
            if key not in properties:
                continue
            value = kwargs[key]
            if not isinstance(value, str):
                continue
            attr_schema = properties[key]
            try:
                if attr_schema.get("type") == "object":
                    value = json.loads(value)
                    if isinstance(value, dict):
                        kwargs[key] = value
                elif attr_schema.get("type") == "array":
                    value = json.loads(value)
                    if isinstance(value, list):
                        kwargs[key] = value
            except (json.JSONDecodeError, ValueError):
                pass

    # Serialize kwargs to JSON
    params = dict(parameters=kwargs)
    try:
        payload = json.dumps(params, default=pydantic_encoder)
    except (TypeError, ValueError) as e:
        raise DeploymentHTTPError(
            f"Failed to serialize request data to JSON: {e}"
        )

    # Construct the invoke endpoint URL
    invoke_url = deployment.url.rstrip("/") + "/invoke"

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Add authorization header if auth_key is present
    if deployment.auth_key:
        headers["Authorization"] = f"Bearer {deployment.auth_key}"

    try:
        step_context = get_step_context()
    except RuntimeError:
        step_context = None

    if step_context:
        # Include these so that the deployment can identify the step
        # and pipeline run that called it, if called from a step.
        headers["ZenML-Step-Name"] = step_context.step_name
        headers["ZenML-Pipeline-Name"] = step_context.pipeline.name
        headers["ZenML-Pipeline-Run-ID"] = str(step_context.pipeline_run.id)
        headers["ZenML-Pipeline-Run-Name"] = step_context.pipeline_run.name

    # Make the HTTP request
    try:
        response = requests.post(
            invoke_url,
            data=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()

        # Try to parse JSON response, fallback to text if not JSON
        try:
            return response.json()
        except ValueError:
            return response.text

    except requests.exceptions.HTTPError as e:
        raise DeploymentHTTPError(
            f"HTTP {e.response.status_code} error calling deployment "
            f"{deployment_name_or_id}: {e.response.text}"
        )
    except requests.exceptions.ConnectionError as e:
        raise DeploymentHTTPError(
            f"Failed to connect to deployment {deployment_name_or_id}: {e}"
        )
    except requests.exceptions.Timeout as e:
        raise DeploymentHTTPError(
            f"Timeout calling deployment {deployment_name_or_id}: {e}"
        )
    except requests.exceptions.RequestException as e:
        raise DeploymentHTTPError(
            f"Request failed for deployment {deployment_name_or_id}: {e}"
        )
