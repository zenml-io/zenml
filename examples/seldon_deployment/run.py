#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import os

import click
from rich import print

from zenml.integrations.seldon.services import (
    SeldonDeploymentConfig,
    SeldonDeploymentService,
)
from zenml.services.service_registry import ServiceRegistry


@click.command()
@click.option("--kubernetes-context", help="Kubernetes context to use.")
@click.option("--namespace", help="Kubernetes namespace to use.")
@click.option("--ingress-hostname", help="Seldon core ingress hostname.")
@click.option(
    "--stop-service",
    is_flag=True,
    default=False,
    help="Stop the prediction service when done",
)
def main(
    kubernetes_context: str,
    namespace: str,
    ingress_hostname: str,
    stop_service: bool,
):
    """Example that deploys a Seldon Core deployment to Kubernetes using a
    Zenml Seldon Core deployment service.

    Example usage:

    ```
    python run.py --kubernetes-context=zenml-eks-sandbox \
        --namespace=zenml-workloads \
        --ingress-hostname=abb84c444c7804aa98fc8c097896479d-377673393.us-east-1.elb.amazonaws.com
    ```

    Args:
        kubernetes_context: Kubernetes context to use.
        namespace: Kubernetes namespace to use.
        ingress_hostname: the ingress hostname used by the Seldon Core
            installation
        stop_service: stop the service when done
    """
    filepath = os.path.join(os.getcwd(), "service.json")
    if not os.path.exists(filepath):
        service_config = SeldonDeploymentConfig(
            kubernetes_context=kubernetes_context,
            namespace=namespace,
            ingress_hostname=ingress_hostname,
            model_uri="gs://seldon-models/v1.14.0-dev/sklearn/iris",
            model_name="iris",
            model_format="sklearn",
            protocol="SKLEARN_SERVER",
            pipeline_name="iris-pipeline",
            pipeline_run_id="78087098790",
            pipeline_step_name="model-deployer",
            replicas=1,
        )
        service = SeldonDeploymentService(config=service_config)
    else:
        with open(filepath, "r") as f:
            service = ServiceRegistry().load_service_from_json(f.read())

    print(f"Deploying service is running: {service.is_running}")
    print(f"Deploying service is stopped: {service.is_stopped}")
    if stop_service:
        service.stop(timeout=120)
    else:
        service.start(timeout=120)
    print(f"Service started: {service.status.prediction_url}")
    print(f"Deploying service is running: {service.is_running}")
    print(f"Deploying service is stopped: {service.is_stopped}")

    with open(filepath, "w") as f:
        f.write(service.json(indent=4))


if __name__ == "__main__":
    main()
