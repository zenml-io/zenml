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
import click

from rich import print

from zenml.integrations.seldon.services import (
    SeldonDeploymentService,
    SeldonDeploymentConfig,
)


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
    service_config = SeldonDeploymentConfig(
        kubernetes_context=kubernetes_context,
        namespace=namespace,
        ingress_hostname=ingress_hostname,
        model_uri="gs://seldon-models/v1.14.0-dev/sklearn/iris",
        model_name="iris",
        model_format="sklearn",
        model_type="sklearn",
        protocol="sklearn",
        pipeline_name="iris-pipeline",
        pipeline_run_id="78087098790",
        pipeline_step_name="model-deployer",
        replicas=2,
    )

    service = SeldonDeploymentService(config=service_config)
    service.start(timeout=20)
    print(f"Service started: {service.status.prediction_url}")


if __name__ == "__main__":
    main()
