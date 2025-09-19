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

import requests
from jsf import JSF
from jsonschema import Draft202012Validator, FormatChecker

from zenml.client import Client
from zenml.deployers.exceptions import (
    DeploymentHTTPError,
    DeploymentInvalidParametersError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
    DeploymentSchemaNotFoundError,
)
from zenml.enums import DeploymentStatus
from zenml.models import DeploymentResponse
from zenml.steps.step_context import get_step_context


def get_deployment_invocation_example(
    deployment: DeploymentResponse,
) -> Dict[str, Any]:
    """Generate an example invocation command for a deployment.

    Args:
        deployment: The deployment for which to generate an example invocation.

    Returns:
        A dictionary containing the example invocation parameters.

    Raises:
        DeploymentSchemaNotFoundError: If the deployment has no associated
            schema for its input parameters.
    """
    if not deployment.snapshot:
        raise DeploymentSchemaNotFoundError(
            f"Deployment {deployment.name} has no associated snapshot."
        )

    if not deployment.snapshot.pipeline_spec:
        raise DeploymentSchemaNotFoundError(
            f"Deployment {deployment.name} has no associated pipeline spec."
        )

    if not deployment.snapshot.pipeline_spec.input_schema:
        raise DeploymentSchemaNotFoundError(
            f"Deployment {deployment.name} has no associated parameters schema."
        )

    input_schema = deployment.snapshot.pipeline_spec.input_schema

    example_generator = JSF(input_schema, allow_none_optionals=0)
    example = example_generator.generate(
        1,
        use_defaults=True,
        use_examples=True,
    )

    return example  # type: ignore[no-any-return]


def call_deployment(
    deployment_name_or_id: Union[str, UUID],
    project: Optional[UUID] = None,
    timeout: int = 300,  # 5 minute timeout
    **kwargs: Any,
) -> Any:
    """Call a deployed deployment and return the result.

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
        DeploymentInvalidParametersError: If the parameters for the
            deployment are invalid.
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
        v = Draft202012Validator(input_schema, format_checker=FormatChecker())
        errors = sorted(v.iter_errors(kwargs), key=lambda e: e.path)
        if errors:
            error_messages = []
            for err in errors:
                path = ""
                if err.path:
                    path = "/".join(list(err.path))
                    error_messages.append(f"{path}: {err.message}")
                else:
                    error_messages.append(f"{err.message}")

            raise DeploymentInvalidParametersError(
                f"Invalid parameters for deployment "
                f"{deployment_name_or_id}: \n" + "\n".join(error_messages)
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

    # TODO: use the current ZenML API token, if any, to authenticate the request
    # if the deployment requires authentication and allows it.

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

    # Serialize kwargs to JSON
    params = dict(parameters=kwargs)
    try:
        payload = json.dumps(params)
    except (TypeError, ValueError) as e:
        raise DeploymentHTTPError(
            f"Failed to serialize request data to JSON: {e}"
        )

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
