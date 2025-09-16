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
    PipelineEndpointDeploymentError,
    PipelineEndpointHTTPError,
    PipelineEndpointInvalidParametersError,
    PipelineEndpointNotFoundError,
    PipelineEndpointSchemaNotFoundError,
)
from zenml.enums import PipelineEndpointStatus
from zenml.models import PipelineEndpointResponse
from zenml.steps.step_context import get_step_context


def get_pipeline_endpoint_invocation_example(
    endpoint: PipelineEndpointResponse,
) -> Dict[str, Any]:
    """Generate an example invocation command for a pipeline endpoint.

    Args:
        endpoint: The pipeline endpoint to invoke.

    Returns:
        A dictionary containing the example invocation parameters.

    Raises:
        PipelineEndpointSchemaNotFoundError: If the pipeline endpoint has no deployment, pipeline spec, or parameters schema.
    """
    if not endpoint.pipeline_deployment:
        raise PipelineEndpointSchemaNotFoundError(
            f"Pipeline endpoint {endpoint.name} has no deployment."
        )

    if not endpoint.pipeline_deployment.pipeline_spec:
        raise PipelineEndpointSchemaNotFoundError(
            f"Pipeline endpoint {endpoint.name} has no pipeline spec."
        )

    if not endpoint.pipeline_deployment.pipeline_spec.parameters_schema:
        raise PipelineEndpointSchemaNotFoundError(
            f"Pipeline endpoint {endpoint.name} has no parameters schema."
        )

    parameters_schema = (
        endpoint.pipeline_deployment.pipeline_spec.parameters_schema
    )

    example_generator = JSF(parameters_schema, allow_none_optionals=0)
    example = example_generator.generate(
        1,
        use_defaults=True,
        use_examples=True,
    )

    return example  # type: ignore[no-any-return]


def call_pipeline_endpoint(
    endpoint_name_or_id: Union[str, UUID],
    project: Optional[UUID] = None,
    timeout: int = 300,  # 5 minute timeout
    **kwargs: Any,
) -> Any:
    """Call a deployed pipeline endpoint and return the result.

    Args:
        endpoint_name_or_id: The name or ID of the pipeline endpoint to call.
        project: The project ID of the pipeline endpoint to call.
        timeout: The timeout for the HTTP request to the pipeline endpoint.
        **kwargs: Keyword arguments to pass to the pipeline endpoint.

    Returns:
        The response from the pipeline endpoint, parsed as JSON if possible,
        otherwise returned as text.

    Raises:
        PipelineEndpointNotFoundError: If the pipeline endpoint is not found.
        PipelineEndpointDeploymentError: If the pipeline endpoint is not running
            or has no URL.
        PipelineEndpointHTTPError: If the HTTP request to the endpoint fails.
        PipelineEndpointInvalidParametersError: If the parameters for the
            pipeline endpoint are invalid.
    """
    client = Client()
    try:
        endpoint = client.get_pipeline_endpoint(
            endpoint_name_or_id, project=project
        )
    except KeyError:
        raise PipelineEndpointNotFoundError(
            f"Pipeline endpoint with name or ID '{endpoint_name_or_id}' "
            f"not found"
        )

    if endpoint.status != PipelineEndpointStatus.RUNNING:
        raise PipelineEndpointDeploymentError(
            f"Pipeline endpoint {endpoint_name_or_id} is not running. Please "
            "refresh or re-deploy the pipeline endpoint or check its logs for "
            "more details."
        )

    if not endpoint.url:
        raise PipelineEndpointDeploymentError(
            f"Pipeline endpoint {endpoint_name_or_id} has no URL. Please "
            "refresh the pipeline endpoint or check its logs for more "
            "details."
        )

    parameters_schema = None
    if (
        endpoint.pipeline_deployment
        and endpoint.pipeline_deployment.pipeline_spec
    ):
        parameters_schema = (
            endpoint.pipeline_deployment.pipeline_spec.parameters_schema
        )

    if parameters_schema:
        v = Draft202012Validator(
            parameters_schema, format_checker=FormatChecker()
        )
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

            raise PipelineEndpointInvalidParametersError(
                f"Invalid parameters for pipeline endpoint "
                f"{endpoint_name_or_id}: \n" + "\n".join(error_messages)
            )

    # Construct the invoke endpoint URL
    invoke_url = endpoint.url.rstrip("/") + "/invoke"

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Add authorization header if auth_key is present
    if endpoint.auth_key:
        headers["Authorization"] = f"Bearer {endpoint.auth_key}"

    # TODO: use the current ZenML API token, if any, to authenticate the request
    # if the pipeline endpoint requires authentication and allows it.

    try:
        step_context = get_step_context()
    except RuntimeError:
        step_context = None

    if step_context:
        # Include these so that the pipeline endpoint can identify the step
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
        raise PipelineEndpointHTTPError(
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
        raise PipelineEndpointHTTPError(
            f"HTTP {e.response.status_code} error calling pipeline endpoint "
            f"{endpoint_name_or_id}: {e.response.text}"
        )
    except requests.exceptions.ConnectionError as e:
        raise PipelineEndpointHTTPError(
            f"Failed to connect to pipeline endpoint {endpoint_name_or_id}: {e}"
        )
    except requests.exceptions.Timeout as e:
        raise PipelineEndpointHTTPError(
            f"Timeout calling pipeline endpoint {endpoint_name_or_id}: {e}"
        )
    except requests.exceptions.RequestException as e:
        raise PipelineEndpointHTTPError(
            f"Request failed for pipeline endpoint {endpoint_name_or_id}: {e}"
        )
