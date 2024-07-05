"""GCP Deployment Manager script to register the ZenML stack with the ZenML Server.

This script expects to be run as a GCP Cloud Function. It receives a JSON
payload containing the full ZenML stack configuration and sends it to the ZenML
Server for registration. It also expects the following environment variables to
be set:

- ZENML_SERVER_URL: The URL of the ZenML Server to register the stack with.
- ZENML_SERVER_API_TOKEN: The API token to use for authentication with the ZenML
    Server.
"""

import os
import urllib.error
import urllib.request
from typing import Any, Tuple

from flask import Request
from sympy import sec


def run_script(request: Request) -> Tuple[Any, int]:
    """Main function to run the script.

    Args:
        request (Request): The Flask request object containing the JSON payload
            to send to the ZenML Server.

    Returns:
        Dict[str, str]: A dictionary containing the status of the script and a
            message.
    """
    payload = request.get_data(as_text=True)
    if not payload:
        return {"status": "error", "message": "No payload received"}, 400

    # Expand secret values in the payload
    for secret_key, secret_value in os.environ.items():
        if secret_key.startswith("ZENML_STACK_SECRET_"):
            secret_key = secret_key.replace("ZENML_STACK_SECRET_", "")
            payload.replace(f"${secret_key}", secret_value)

    print(f"Received payload: {payload}")

    try:
        url = (
            os.environ["ZENML_SERVER_URL"].lstrip("/")
            + "/api/v1/workspaces/default/full-stack"
        )
        api_token = os.environ["ZENML_SERVER_API_TOKEN"]

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        data = payload.encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                status_code = response.getcode()
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status_code = e.code
            response_body = e.read().decode("utf-8")

        print(status_code)
        print(response_body)

        if status_code == 200:
            return (
                {
                    "status": "success",
                    "message": "Stack successfully registered with ZenML",
                },
                200,
            )
        else:
            return {
                "status": "failed",
                "message": (
                    f"Failed to register the ZenML stack. The ZenML Server "
                    f"replied with HTTP status code {status_code}: "
                    f"{response_body}"
                ),
            }, 400

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "status": "failed",
            "message": f"Failed to register the ZenML stack: {str(e)}",
        }, 500
