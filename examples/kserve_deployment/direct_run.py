from zenml.integrations.kserve.model_deployers.kserve_model_deployer import (
    KServeModelDeployer,
)
from zenml.integrations.kserve.services.kserve_deployment import (
    KServeDeploymentConfig,
)


def main():

    model_deployer = KServeModelDeployer.get_active_model_deployer()
    model_deployer.deploy_model(
        config=KServeDeploymentConfig(
            model_uri="gs://kfserving-examples/models/sklearn/1.0/model",
            model_name="iris",
            predictor="sklearn",
            resources={"requests": {"cpu": "100m"}},
        ),
        replace=True,
    )


if __name__ == "__main__":
    main()
