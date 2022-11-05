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
"""Implementation of the MLflow model deployer pipeline step."""
import os
import tempfile
from typing import Dict, List, Optional, Type, cast

import bentoml
import torch
from bentoml import bentos

from zenml.artifacts.model_artifact import ModelArtifact
from zenml.constants import DEFAULT_SERVICE_START_STOP_TIMEOUT
from zenml.environment import Environment
from zenml.integrations.bentoml.model_deployers.bentoml_model_deployer import (
    BentoMLModelDeployer,
)
from zenml.integrations.bentoml.services.bentoml_deployment import (
    BentoMLDeploymentConfig,
    BentoMLDeploymentService,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseParameters,
    BaseStep,
    StepEnvironment,
    step,
)
from zenml.steps.step_context import StepContext

logger = get_logger(__name__)


class BentoMLBuilderParameters(BaseParameters):
    """Model deployer step parameters for MLflow.

    Attributes:
        model_name: the name of the MLflow model logged in the MLflow artifact
            store for the current pipeline.
        experiment_name: Name of the MLflow experiment in which the model was
            logged.
        run_name: Name of the MLflow run in which the model was logged.
        workers: number of workers to use for the prediction service
        mlserver: set to True to use the MLflow MLServer backend (see
            https://github.com/SeldonIO/MLServer). If False, the
            MLflow built-in scoring server will be used.
        timeout: the number of seconds to wait for the service to start/stop.
    """

    service: str
    model_name: str
    model_type: str
    version: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    include: Optional[List[str]] = None
    exclude: Optional[List[str]] = None
    python: Optional[Dict[str, str]] = None
    docker: Optional[Dict[str, str]] = None
    port: int
    workers: int = None
    backlog: int = None
    production: bool = False
    working_dir: str = None
    host: str = None
    timeout: int = DEFAULT_SERVICE_START_STOP_TIMEOUT * 2


def bento_deployer(
    model: ModelArtifact,
    params: BentoMLBuilderParameters,
    context: StepContext,
) -> None:
    """Build a bentoML Model and Bneto and save it"""

    if params.model_type == "tensorflow":
        bento_model = bentoml.tensorflow.save_model(
            params.model_name,
            model,
            signatures={"__call__": {"batchable": True, "batch_dim": 0}},
            labels=params.labels,
        )
    elif params.model_type == "sklearn":
        bento_model = bentoml.sklearn.save_model(
            params.model_name,
            model,
            signatures={"predict": {"batchable": True, "batch_dim": 0}},
        )
    elif params.model_type == "pytorch":
        with fileio.open(os.path.join(model.uri, "entire_model.pt"), "rb") as f:
            model = torch.load(f)
        bento_model = bentoml.pytorch.save_model(
            params.model_name,
            model,
            signatures={"__call__": {"batchable": True, "batchdim": 0}},
        )
    elif params.model_type == "transformers":
        bento_model = bentoml.transformers.save_model(
            params.model_name,
            model,
            signatures={"__call__": {"batchable": True, "batchdim": 0}},
        )
    elif params.model_type == "xgboost":
        bento_model = bentoml.xgboost.save_model(
            params.model_name,
            model,
        )
    else:
        bento_model = bentoml.picklable_model.save_model(
            params.model_name,
            model,
            signatures={"batchable": True, "batch_dim": 0},
        )

    logger.info(
        f"model saved {bento_model}",
    )
    
    bento = bentos.build(
        service=params.service,
        version=params.version,
        labels=params.labels,
        description=params.description,
        include=params.include,
        exclude=params.exclude,
        python=params.python,
        docker=params.docker,
        build_ctx=params.working_dir,
    )

    temp_dir = tempfile.TemporaryDirectory()

    exported = bentos.export_bento(bento.tag, temp_dir.name)

    exported_bento_uri = os.path.join(
        context.get_output_artifact_uri(), "bentos"
    )
    fileio.makedirs(exported_bento_uri)

    fileio.copy(exported, os.path.join(exported_bento_uri, str(bento.tag)))

    return (str(bento.tag), os.path.join(exported_bento_uri, str(bento.tag)))


@step(enable_cache=False)
def bentoml_model_deployer_step(
    deploy_decision: bool,
    model: ModelArtifact,
    params: BentoMLBuilderParameters,
    context: StepContext,
) -> BentoMLDeploymentService:
    """Model deployer pipeline step for BentoML.

    # noqa: DAR401

    Args:
        deploy_decision: whether to deploy the model or not
        model: the model artifact to deploy
        params: parameters for the deployer step

    Returns:
        BentoML deployment service
    """

    from zenml.client import Client

    repo_path = Client.find_repository()
    if not repo_path:
        raise ValueError("No ZenML repository found.")

    if params.working_dir is None:
        params.working_dir = str(repo_path)

    model_deployer = cast(
        BentoMLModelDeployer, BentoMLModelDeployer.get_active_model_deployer()
    )

    # get pipeline name, step name and run id
    step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
    pipeline_name = step_env.pipeline_name
    run_id = step_env.pipeline_run_id
    step_name = step_env.step_name

    bento, bento_uri = bento_deployer(model, params, context=context)

    # fetch existing services with same pipeline name, step name and model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=params.model_name,
    )

    # create a config for the new model service
    predictor_cfg = BentoMLDeploymentConfig(
        model_name=params.model_name,
        bento=bento,
        model_uri=bento_uri,
        workers=params.workers,
        working_dir=params.working_dir,
        port=params.port,
        pipeline_name=pipeline_name,
        pipeline_run_id=run_id,
        pipeline_step_name=step_name,
    )

    # Creating a new service with inactive state and status by default
    service = BentoMLDeploymentService(predictor_cfg)
    if existing_services:
        service = cast(BentoMLDeploymentService, existing_services[0])

    if not deploy_decision and existing_services:
        logger.info(
            f"Skipping model deployment because the model quality does not "
            f"meet the criteria. Reusing last model server deployed by step "
            f"'{step_name}' and pipeline '{pipeline_name}' for model "
            f"'{params.model_name}'..."
        )
        if not service.is_running:
            service.start(timeout=params.timeout)
        return service

    # create a new model deployment and replace an old one if it exists
    new_service = cast(
        BentoMLDeploymentService,
        model_deployer.deploy_model(
            replace=True,
            config=predictor_cfg,
            timeout=params.timeout,
        ),
    )

    logger.info(
        f"BentoML deployment service started and reachable at:\n"
        f"    {new_service.prediction_url}\n"
    )

    return new_service


def bentoml_deployer_step(
    enable_cache: bool = True,
    name: Optional[str] = None,
) -> Type[BaseStep]:
    """Creates a pipeline step to deploy a given ML model with a local MLflow prediction server.

    The returned step can be used in a pipeline to implement continuous
    deployment for an MLflow model.

    Args:
        enable_cache: Specify whether caching is enabled for this step. If no
            value is passed, caching is enabled by default
        name: Name of the step.

    Returns:
        an MLflow model deployer pipeline step
    """
    logger.warning(
        "The `mlflow_deployer_step` function is deprecated. Please "
        "use the built-in `mlflow_model_deployer_step` step instead."
    )
    return bentoml_model_deployer_step
