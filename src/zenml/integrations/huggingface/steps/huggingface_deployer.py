"""Implementation of the Huggingface Deployer step."""
from typing import cast

from zenml import get_step_context, step
from zenml.integrations.huggingface.model_deployers.huggingface_model_deployer import (
    HuggingFaceModelDeployer,
)
from zenml.integrations.huggingface.services.huggingface_deployment import (
    HuggingFaceDeploymentService,
    HuggingFaceServiceConfig,
)
from zenml.logger import get_logger
from zenml.model_deployers.base_model_deployer import (
    DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
)

logger = get_logger(__name__)


@step(enable_cache=False)
def huggingface_model_deployer_step(
    service_config: HuggingFaceServiceConfig,
    deploy_decision: bool = True,
    timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
) -> HuggingFaceDeploymentService:
    """Huggingface model deployer pipeline step.

    This step can be used in a pipeline to implement continuous
    deployment with Huggingface Inference Endpoint.

    Args:
        service_config: Huggingface deployment service configuration.
        deploy_decision: whether to deploy the model or not
        timeout: the timeout in seconds to wait for the deployment to start

    Returns:
        Huggingface deployment service
    """
    model_deployer = cast(
        HuggingFaceModelDeployer,
        HuggingFaceModelDeployer.get_active_model_deployer(),
    )

    # get pipeline name, step name and run id
    context = get_step_context()
    pipeline_name = context.pipeline.name
    run_name = context.pipeline_run.name
    step_name = context.step_run.name

    # update the step configuration with the real pipeline runtime information
    service_config = service_config.copy()
    service_config.pipeline_name = pipeline_name
    service_config.run_name = run_name
    service_config.pipeline_step_name = step_name

    # fetch existing services with same pipeline name, step name and
    # model name
    existing_services = model_deployer.find_model_server(
        pipeline_name=pipeline_name,
        pipeline_step_name=step_name,
        model_name=service_config.model_name,
    )

    # even when the deploy decision is negative, if an existing model server
    # is not running for this pipeline/step, we still have to serve the
    # current model, to ensure that a model server is available at all times
    if not deploy_decision and existing_services:
        logger.info(
            f"Skipping model deployment because the model quality does not "
            f"meet the criteria. Reusing last model server deployed by step "
            f"'{step_name}' and pipeline '{pipeline_name}' for model "
            f"'{service_config.model_name}'..."
        )
        service = cast(HuggingFaceDeploymentService, existing_services[0])
        # even when the deploy decision is negative, we still need to start
        # the previous model server if it is no longer running, to ensure that
        # a model server is available at all times
        if not service.is_running:
            service.start(timeout=timeout)
        return service

    # invoke the Huggingface model deployer to create a new service
    # or update an existing one that was previously deployed for the same
    # model
    service = cast(
        HuggingFaceDeploymentService,
        model_deployer.deploy_model(
            service_config, replace=True, timeout=timeout
        ),
    )

    logger.info(
        f"Huggingface deployment service started and reachable at:\n"
        f"    {service.prediction_url}\n"
    )

    return service
